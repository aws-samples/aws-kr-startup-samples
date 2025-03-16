#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os
import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_ecr,
  aws_ecr_assets,
)
from constructs import Construct
import cdk_ecr_deployment as ecr_deploy


class ECRStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    ecr_repository = self.node.try_get_context('ecr')
    repository_name = ecr_repository['repository_name']

    image = aws_ecr_assets.DockerImageAsset(self, "MyBuildImage",
      directory=os.path.join(os.path.dirname(__file__), '../src/container'),
      asset_name=repository_name,
      build_args={
        "CUDA_VERSION": "12.4.1",
      },
      invalidation=aws_ecr_assets.DockerImageAssetInvalidationOptions(
        build_args=False
      )
    )

    repository = aws_ecr.Repository(self, f"{repository_name}ECRRepository",
      empty_on_delete=True,
      encryption=aws_ecr.RepositoryEncryption.AES_256,
      removal_policy=cdk.RemovalPolicy.DESTROY,
      repository_name=repository_name
    )

    # delete images older than 7 days
    repository.add_lifecycle_rule(
      max_image_age=cdk.Duration.days(7),
      rule_priority=1,
      tag_status=aws_ecr.TagStatus.UNTAGGED
    )

    # keep last 3 images
    repository.add_lifecycle_rule(
      max_image_count=3,
      rule_priority=2,
      tag_status=aws_ecr.TagStatus.ANY
    )

    # src_docker_image_version = ecr_repository['docker_image_name']
    image_version = ecr_repository.get('tag', 'latest')
    deploy_image_versions = image_version if image_version == "latest" else list(set([image_version, "latest"]))
    for idx, deploy_image_version in enumerate(deploy_image_versions):
      ecr_deploy.ECRDeployment(self, f"{repository_name}ECRDeployment-{idx:0>3}",
        src=ecr_deploy.DockerImageName(image.image_uri),
        dest=ecr_deploy.DockerImageName(repository.repository_uri_for_tag_or_digest(deploy_image_version))
      )
