// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

import { App } from "aws-cdk-lib";
import { Template, Match } from "aws-cdk-lib/assertions";
import { SlackBotStack } from "../src/stack";

test("Snapshot", () => {
	const app = new App();
	const stack = new SlackBotStack(app, "test", {});

	const template = Template.fromStack(stack);
	expect(template.toJSON()).toMatchSnapshot();
});

test("Non-rotating secret", () => {
	const app = new App();
	const stack = new SlackBotStack(app, "test", {});

	const template = Template.fromStack(stack);
	template.resourceCountIs("AWS::SecretsManager::Secret", 1);
	template.resourceCountIs("AWS::SecretsManager::RotationSchedule", 0);
});

test("Lambda has access", () => {
	const app = new App();
	const stack = new SlackBotStack(app, "test", {});

	const template = Template.fromStack(stack);
	template.hasResourceProperties("AWS::IAM::Policy", {
		PolicyDocument: {
			Statement: Match.arrayWith([
				{
					Action: "bedrock:InvokeModel",
					Effect: "Allow",
					Resource: "*",
				},
				Match.objectLike({
					Action: ["secretsmanager:GetSecretValue", "secretsmanager:DescribeSecret"],
					Effect: "Allow",
				}),
			]),
		},
	});
});

test("Has Outputs", () => {
	const app = new App();
	const stack = new SlackBotStack(app, "test", {});

	const template = Template.fromStack(stack);
	template.hasOutput("SlackBotEndpointOutput", {
		Value: Match.anyValue(),
	});
	template.hasOutput("SlackBotTokenOutput", {
		Value: Match.anyValue(),
	});
});
