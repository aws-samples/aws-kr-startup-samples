import boto3
import time
import json
from typing import Dict, Any

codebuild = boto3.client('codebuild')

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    print(f"Received event: {json.dumps(event)}")
    
    if event['RequestType'] in ['Create', 'Update']:
        project_names = event['ResourceProperties']['ProjectNames']
        return check_build_status(project_names)
    elif event['RequestType'] == 'Delete':
        # Nothing to do on delete
        return {'PhysicalResourceId': event.get('PhysicalResourceId', 'codebuild-status-checker')}
    else:
        raise Exception(f"Unsupported request type: {event['RequestType']}")

def check_build_status(project_names: list) -> Dict[str, Any]:
    max_attempts = 180  # Maximum number of attempts (15 minutes with 5-second intervals)
    attempt = 0

    while attempt < max_attempts:
        all_succeeded = True
        for project_name in project_names:
            builds = codebuild.list_builds_for_project(projectName=project_name, sortOrder='DESCENDING')
            if not builds['ids']:
                print(f"No builds found for project {project_name}")
                all_succeeded = False
                break

            build_id = builds['ids'][0]
            build_info = codebuild.batch_get_builds(ids=[build_id])['builds'][0]
            build_status = build_info['buildStatus']

            if build_status == 'SUCCEEDED':
                print(f"Build for project {project_name} succeeded")
            elif build_status in ['IN_PROGRESS', 'QUEUED']:
                print(f"Build for project {project_name} is still in progress")
                all_succeeded = False
                break
            else:
                raise Exception(f"Build for project {project_name} failed with status: {build_status}")

        if all_succeeded:
            return {
                'PhysicalResourceId': 'codebuild-status-checker',
                'Data': {
                    'Message': 'All CodeBuild projects completed successfully'
                }
            }

        attempt += 1
        time.sleep(5)  # Wait for 5 seconds before checking again

    raise Exception("Timed out waiting for CodeBuild projects to complete")
