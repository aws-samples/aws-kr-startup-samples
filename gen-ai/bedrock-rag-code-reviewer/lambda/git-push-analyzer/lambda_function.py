import json
import os
import boto3
import hashlib
import requests
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import tree_sitter_javascript as tsjavascript
import tree_sitter_python as tspython
from tree_sitter import Language, Parser
import yaml
import zipfile

# === CONFIG ===
S3_BUCKET = os.environ.get("S3_BUCKET")
CODEBASE_S3_PREFIX = os.environ.get("CODEBASE_S3_PREFIX", "codebase/")
REPORT_S3_PREFIX = os.environ.get("REPORT_S3_PREFIX", "reports/")
KB_ID = os.environ.get("KB_ID")
REGION = os.environ.get("AWS_REGION")
DATA_SOURCE_ID = os.environ.get("DATA_SOURCE_ID")
MODEL_ARN = os.environ.get("MODEL_ARN")
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

# Chunking configuration
# INCLUDE_FILE_PATH_IN_CHUNKS: When true, includes full file path context in chunks for better retrieval
# When false, only the raw code content is embedded (better for pure code similarity)
INCLUDE_FILE_PATH_IN_CHUNKS = os.environ.get("INCLUDE_FILE_PATH_IN_CHUNKS", "true").lower() == "true"

# Initialize Tree-sitter parsers
JS_LANGUAGE = Language(tsjavascript.language())
js_parser = Parser(JS_LANGUAGE)

PY_LANGUAGE = Language(tspython.language())
py_parser = Parser(PY_LANGUAGE)

# Initialize AWS clients
s3_client = boto3.client("s3", region_name=REGION)
bedrock_client = boto3.client("bedrock-agent", region_name=REGION)

def lambda_handler(event, context):
    """Main Lambda handler for analyzing GitHub repository
    
    Supports two modes:
    1. Push mode (default): Analyze only changed files from a push event
    2. Full index mode: Index the entire codebase (for initial setup)
    
    Event structure for push mode:
    {
        "push_info": {...},
        "webhook_payload": {...}
    }
    
    Event structure for full index mode:
    {
        "mode": "full_index",
        "repository": {
            "full_name": "owner/repo",
            "default_branch": "main",  # optional, defaults to "main"
            "default_branch_sha": "sha"  # optional, defaults to latest
        }
    }
    """
    
    try:
        # Determine operation mode
        mode = event.get('mode', 'push')  # 'push' or 'full_index'
        
        if mode == 'full_index':
            # Full repository indexing mode
            return handle_full_index(event, context)
        else:
            # Push analysis mode (default)
            return handle_push_analysis(event, context)
            
    except Exception as e:
        import traceback
        print(f"Error in lambda handler: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def handle_push_analysis(event, context):
    """Handle push event analysis (original functionality)"""
    push_info = event.get('push_info')
    
    if not push_info:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'push_info required in event payload'})
        }
    
    print(f"Analyzing push: {push_info['commits_count']} commits to {push_info['branch']}")
    
    # Download repository at head commit
    repo_path = download_repository(push_info)
    
    try:
        # Get changed files from push commits
        changed_files = get_push_changed_files(push_info, repo_path)
        
        if not changed_files:
            print("No relevant files changed in this push")
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'No relevant files changed'})
            }
        
        # Process and analyze changes
        process_push_changes(push_info, changed_files, repo_path)
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Push analysis completed successfully'})
        }
    finally:
        # Always cleanup
        cleanup_temp_files(repo_path)

def handle_full_index(event, context):
    """Handle full repository indexing"""
    # Extract repository information
    repo_info = event.get('repository')
    if not repo_info:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'repository information required for full indexing'})
        }
    
    print(f"Starting full repository indexing for {repo_info.get('full_name', 'unknown')}")
    
    # Get default branch info if not provided
    if not repo_info.get('default_branch_sha'):
        # Get the latest commit SHA for the default branch
        headers = {'Authorization': f'token {GITHUB_TOKEN}'} if GITHUB_TOKEN else {}
        branch = repo_info.get('default_branch', 'main')
        api_url = f"https://api.github.com/repos/{repo_info['full_name']}/branches/{branch}"
        
        try:
            response = requests.get(api_url, headers=headers)
            response.raise_for_status()
            branch_data = response.json()
            repo_info['default_branch_sha'] = branch_data['commit']['sha']
        except Exception as e:
            print(f"Failed to get latest commit SHA, using branch name: {e}")
            repo_info['default_branch_sha'] = branch
    
    # Create a synthetic push_info for repository download
    push_info = {
        'repo_full_name': repo_info['full_name'],
        'head_sha': repo_info['default_branch_sha'],
        'branch': repo_info.get('default_branch', 'main')
    }
    
    # Download repository
    repo_path = download_repository(push_info)
    
    try:
        # Get all relevant files in the repository
        all_files = get_all_repository_files(repo_path)
        
        if not all_files:
            print("No relevant files found in repository")
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'No relevant files found in repository'})
            }
        
        print(f"Found {len(all_files)} files to index")
        
        # Process all files for indexing
        chunks_count = process_full_index(repo_info, all_files, repo_path)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Full repository indexing completed successfully',
                'files_indexed': len(all_files),
                'chunks_created': chunks_count
            })
        }
    finally:
        # Always cleanup
        cleanup_temp_files(repo_path)

def get_all_repository_files(repo_path):
    """Get all relevant files in the repository for full indexing"""
    relevant_extensions = {'.js', '.ts', '.py', '.pyw', '.yaml', '.yml'}
    all_files = []
    
    for root, dirs, files in os.walk(repo_path):
        # Skip common directories that shouldn't be indexed
        dirs[:] = [d for d in dirs if d not in ['node_modules', '.git', '__pycache__', '.venv', 'venv', 'dist', 'build']]
        
        for file in files:
            if any(file.endswith(ext) for ext in relevant_extensions):
                filepath = os.path.join(root, file)
                relative_path = os.path.relpath(filepath, repo_path)
                
                all_files.append({
                    'filename': relative_path,
                    'full_path': filepath,
                    'status': 'added',  # Treat all as added for initial index
                })
    
    return all_files

def process_full_index(repo_info, all_files, repo_path):
    """Process all files for full repository indexing"""
    # Generate chunks for all files
    chunks = chunk_changed_files(all_files, repo_path)
    print(f"Generated {len(chunks)} chunks from {len(all_files)} files")
    
    # Upload chunks to S3
    if chunks:
        # Use a special commit hash for full index
        commit_hash = f"full-index-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        upload_chunks_to_s3(chunks, commit_hash)
        
        # Trigger KB sync
        trigger_kb_sync()
    
    # Send notification about full index completion
    if SLACK_WEBHOOK_URL:
        send_full_index_notification(repo_info, len(all_files), len(chunks))
    
    return len(chunks)

def send_full_index_notification(repo_info, files_count, chunks_count):
    """Send Slack notification for full index completion"""
    try:
        payload = {
            "text": f"📚 Full Repository Index Complete: {repo_info.get('full_name', 'unknown')}",
            "attachments": [{
                "color": "#36a64f",
                "fields": [
                    {
                        "title": "Repository",
                        "value": repo_info.get('full_name', 'unknown'),
                        "short": True
                    },
                    {
                        "title": "Statistics",
                        "value": f"Files: {files_count}\nChunks: {chunks_count}",
                        "short": True
                    },
                    {
                        "title": "Status",
                        "value": "✅ Knowledge Base updated",
                        "short": False
                    }
                ]
            }]
        }
        
        response = requests.post(SLACK_WEBHOOK_URL, json=payload)
        response.raise_for_status()
        print(f"✅ Slack notification sent for full index")
        
    except Exception as e:
        print(f"❌ Failed to send Slack notification: {e}")

def download_repository(push_info):
    """Download repository at the head commit"""
    temp_dir = tempfile.mkdtemp()
    repo_path = os.path.join(temp_dir, 'repo')
    
    # Use GitHub API to download repository archive
    headers = {'Authorization': f'token {GITHUB_TOKEN}'} if GITHUB_TOKEN else {}
    
    # Download repository at head commit
    api_url = f"https://api.github.com/repos/{push_info['repo_full_name']}/zipball/{push_info['head_sha']}"
    response = requests.get(api_url, headers=headers)
    response.raise_for_status()
    
    # Extract zip file
    zip_path = os.path.join(temp_dir, 'repo.zip')
    with open(zip_path, 'wb') as f:
        f.write(response.content)
    
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)
    
    # Find the extracted directory (GitHub creates a directory with repo name and commit hash)
    extracted_dirs = [d for d in os.listdir(temp_dir) if os.path.isdir(os.path.join(temp_dir, d)) and d != 'repo']
    if extracted_dirs:
        extracted_path = os.path.join(temp_dir, extracted_dirs[0])
        shutil.move(extracted_path, repo_path)
    
    return repo_path

def get_push_changed_files(push_info, repo_path):
    """Get list of changed files from push commits using GitHub API"""
    headers = {'Authorization': f'token {GITHUB_TOKEN}'} if GITHUB_TOKEN else {}
    
    # Filter for relevant file types and existing files
    relevant_extensions = {'.js', '.ts', '.py', '.pyw', '.yaml', '.yml'}
    changed_files = []
    unique_files = {}  # Track unique files to avoid duplicates
    
    # Process each commit in the push
    for commit in push_info['commits']:
        commit_sha = commit['id']
        
        # Get detailed commit info with file changes
        api_url = f"https://api.github.com/repos/{push_info['repo_full_name']}/commits/{commit_sha}"
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        
        commit_data = response.json()
        
        if 'files' not in commit_data:
            continue
            
        for file_info in commit_data['files']:
            filename = file_info['filename']
            file_path = os.path.join(repo_path, filename)
            
            # Check if file has relevant extension and exists (or existed)
            if any(filename.endswith(ext) for ext in relevant_extensions):
                # Use filename as key to avoid duplicates, but keep latest version
                unique_files[filename] = {
                    'filename': filename,
                    'status': file_info['status'],
                    'additions': file_info.get('additions', 0),
                    'deletions': file_info.get('deletions', 0),
                    'patch': file_info.get('patch', ''),
                    'full_path': file_path,
                    'commit_sha': commit_sha
                }
    
    # Convert to list and filter for existing files (unless deleted)
    for filename, file_info in unique_files.items():
        if file_info['status'] == 'removed' or os.path.exists(file_info['full_path']):
            changed_files.append(file_info)
    
    print(f"Found {len(changed_files)} relevant changed files across {len(push_info['commits'])} commits")
    return changed_files

def process_push_changes(push_info, changed_files, repo_path):
    """Process and analyze the push changes"""
    # Generate chunks for changed files
    chunks = chunk_changed_files(changed_files, repo_path)
    print(f"Generated {len(chunks)} chunks from changed files")
    
    # Upload chunks to S3
    if chunks:
        upload_chunks_to_s3(chunks, push_info['head_sha'])
        
        # Trigger KB sync
        trigger_kb_sync()
    
    # Generate and send analysis report
    create_push_analysis_report(push_info, changed_files)

def chunk_changed_files(changed_files, repo_path):
    """Generate chunks for changed files"""
    all_chunks = []
    
    for file_info in changed_files:
        filepath = Path(file_info['full_path'])
        
        if not filepath.exists():
            continue
            
        try:
            # Get relative path from repo root for stable ID generation
            relative_path = os.path.relpath(str(filepath), repo_path)
            
            if file_info['filename'].endswith(('.js', '.ts')):
                code = filepath.read_text(encoding='utf-8')
                all_chunks.extend(chunk_js_code(filepath, code, relative_path))
            elif file_info['filename'].endswith(('.py', '.pyw')):
                code = filepath.read_text(encoding='utf-8')
                all_chunks.extend(chunk_py_code(filepath, code, relative_path))
            elif file_info['filename'].endswith(('.yaml', '.yml')):
                all_chunks.extend(chunk_yaml_file(filepath, relative_path))
        except Exception as e:
            print(f"Error processing file {filepath}: {e}")
            
    return all_chunks

def generate_stable_id(filepath: str, chunk_type: str, chunk_name: str) -> str:
    """Generate stable ID for chunks"""
    return hashlib.sha256(f"{filepath}:{chunk_type}:{chunk_name}".encode("utf-8")).hexdigest()

def create_semantic_chunk_content(chunk_data: dict) -> str:
    """Create semantic content for chunk based on configuration"""
    if not INCLUDE_FILE_PATH_IN_CHUNKS:
        # Return only the code content
        return chunk_data['content']
    
    # Create context lines with full filepath
    context_lines = []
    
    # Add the full filepath
    context_lines.append(f"{chunk_data['filepath']}")
    
    # Combine context with code
    return f"{chr(10).join(context_lines)}\n\n{chunk_data['content']}"

def chunk_js_code(filepath: Path, code: str, relative_path: str):
    """Chunk JavaScript/TypeScript code"""
    tree = js_parser.parse(bytes(code, "utf8"))
    root = tree.root_node
    chunks = []
    
    for node in root.children:
        if node.type in ["function_declaration", "class_declaration"]:
            name = code[node.children[1].start_byte:node.children[1].end_byte]
            chunk = code[node.start_byte:node.end_byte]
            chunks.append({
                "id": generate_stable_id(relative_path, node.type, name),
                "type": node.type,
                "name": name,
                "filepath": relative_path,
                "language": "javascript",
                "content": chunk
            })
    return chunks

def chunk_py_code(filepath: Path, code: str, relative_path: str):
    """Chunk Python code"""
    tree = py_parser.parse(bytes(code, "utf8"))
    root = tree.root_node
    chunks = []
    
    for node in root.children:
        if node.type in ["function_definition", "class_definition"]:
            name = code[node.children[1].start_byte:node.children[1].end_byte]
            chunk = code[node.start_byte:node.end_byte]
            chunks.append({
                "id": generate_stable_id(relative_path, node.type, name),
                "type": node.type,
                "name": name,
                "filepath": relative_path,
                "language": "python",
                "content": chunk
            })
    return chunks

def chunk_yaml_file(filepath: Path, relative_path: str):
    """Chunk YAML files"""
    chunks = []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            docs = list(yaml.safe_load_all(f))
    except Exception:
        return []

    for i, doc in enumerate(docs):
        if not isinstance(doc, dict):
            continue
            
        if 'kind' in doc and 'metadata' in doc:
            name = doc['metadata'].get('name', f"unnamed-{i}")
            chunks.append({
                "id": generate_stable_id(relative_path, "kubernetes_resource", f"{doc['kind']}/{name}"),
                "type": "kubernetes_resource",
                "name": f"{doc['kind']}/{name}",
                "filepath": relative_path,
                "language": "yaml",
                "content": yaml.dump(doc)
            })
        else:
            for key in doc:
                chunks.append({
                    "id": generate_stable_id(relative_path, "helm_values_section", key),
                    "type": "helm_values_section",
                    "name": key,
                    "filepath": relative_path,
                    "language": "yaml",
                    "content": yaml.dump({key: doc[key]})
                })
    return chunks

def upload_chunks_to_s3(chunks, commit_hash):
    """Upload chunks to S3 with semantic content for embeddings and separate metadata files"""
    with tempfile.TemporaryDirectory() as temp_dir:
        for chunk in chunks:
            # Create semantic content for embedding
            semantic_content = create_semantic_chunk_content(chunk)
            
            # Write semantic content to file
            content_filename = os.path.join(temp_dir, f"{chunk['id']}.txt")
            with open(content_filename, "w", encoding="utf-8") as f:
                f.write(semantic_content)
            
            # Create metadata file in Bedrock Knowledge Base format
            metadata = {
                "metadataAttributes": {
                    "chunk_type": {
                        "value": {
                            "type": "STRING",
                            "stringValue": chunk['type']
                        },
                        "includeForEmbedding": False
                    },
                    "chunk_name": {
                        "value": {
                            "type": "STRING", 
                            "stringValue": chunk['name']
                        },
                        "includeForEmbedding": False
                    },
                    "chunk_filepath": {
                        "value": {
                            "type": "STRING",
                            "stringValue": chunk['filepath']
                        },
                        "includeForEmbedding": False
                    },
                    "language": {
                        "value": {
                            "type": "STRING",
                            "stringValue": chunk['language']
                        },
                        "includeForEmbedding": False
                    },
                    "chunk_id": {
                        "value": {
                            "type": "STRING",
                            "stringValue": chunk['id']
                        },
                        "includeForEmbedding": False
                    },
                    "commit": {
                        "value": {
                            "type": "STRING",
                            "stringValue": commit_hash
                        },
                        "includeForEmbedding": False
                    }
                }
            }
            
            # Metadata filename must match: {content_file}.metadata.json
            metadata_filename = os.path.join(temp_dir, f"{chunk['id']}.txt.metadata.json")
            with open(metadata_filename, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)
            
            # Upload content file
            content_key = CODEBASE_S3_PREFIX + f"{chunk['id']}.txt"
            s3_client.upload_file(
                Filename=content_filename,
                Bucket=S3_BUCKET,
                Key=content_key,
                ExtraArgs={
                    "ContentType": "text/plain"
                }
            )
            
            # Upload metadata file with correct naming convention
            metadata_key = CODEBASE_S3_PREFIX + f"{chunk['id']}.txt.metadata.json"
            s3_client.upload_file(
                Filename=metadata_filename,
                Bucket=S3_BUCKET,
                Key=metadata_key,
                ExtraArgs={
                    "ContentType": "application/json"
                }
            )
            
            print(f"Uploaded chunk and metadata to s3://{S3_BUCKET}/{content_key}")

def trigger_kb_sync():
    """Trigger Bedrock Knowledge Base sync"""
    try:
        bedrock_client.start_ingestion_job(
            knowledgeBaseId=KB_ID,
            dataSourceId=DATA_SOURCE_ID
        )
        print("🚀 Bedrock Knowledge Base sync triggered")
    except Exception as e:
        print(f"❌ Failed to trigger KB sync: {e}")

def create_push_analysis_report(push_info, changed_files):
    """Create and send push analysis report"""
    if not changed_files:
        print("No changed files to analyze")
        return
    
    all_summaries = []
    
    for file_info in changed_files:
        if not file_info.get('patch'):
            continue
            
        prompt = f"""
You are a senior developer assistant analyzing a push to the main/master branch.

Summarize the changes in this file using this format:

### File: {file_info['filename']}
**Summary**: <brief overview of the change>
**Intent**: <what the developer intended to do>
**Impact**: <what parts of the system may be affected, including edge cases>
**Risk Assessment**: <potential risks or concerns>

Push Information:
- Branch: {push_info['branch']}
- Pusher: {push_info['pusher']}
- Commits: {push_info['commits_count']}
- Head Commit: {push_info['head_sha'][:8]}
- Pushed at: {push_info['pushed_at']}

File Changes:
- Status: {file_info['status']}
- Additions: {file_info['additions']}
- Deletions: {file_info['deletions']}
- Commit: {file_info.get('commit_sha', 'unknown')[:8]}

```diff
{file_info['patch']}
```
"""
        
        try:
            summary = retrieve_and_generate(prompt)
            all_summaries.append(f"### {file_info['filename']}\n{summary.strip()}\n")
        except Exception as e:
            print(f"❌ Failed to generate summary for {file_info['filename']}: {e}")
    
    if not all_summaries:
        print("No summaries generated")
        return
    
    # Create final report
    report_header = f"""# Push Analysis Report

**Branch**: {push_info['branch']}
**Pusher**: {push_info['pusher']}
**Commits**: {push_info['commits_count']}
**Head Commit**: {push_info['head_sha'][:8]}
**Pushed at**: {push_info['pushed_at']}

---

"""
    
    final_report = report_header + "\n\n".join(all_summaries)
    
    # Save report to S3
    report_key = f"{REPORT_S3_PREFIX}push-analysis-{push_info['branch']}-{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}.md"
    
    try:
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=report_key,
            Body=final_report.encode("utf-8"),
            ContentType="text/markdown"
        )
        print(f"✅ Report uploaded to s3://{S3_BUCKET}/{report_key}")
    except Exception as e:
        print(f"❌ Failed to upload report: {e}")
    
    # Send to Slack if Slack webhook URL is set
    if SLACK_WEBHOOK_URL:
        send_slack_notification(push_info, final_report, report_key)

def retrieve_and_generate(prompt):
    """Use Bedrock RAG to generate analysis"""
    agent_client = boto3.client("bedrock-agent-runtime", region_name=REGION)
    
    response = agent_client.retrieve_and_generate(
        input={"text": prompt},
        retrieveAndGenerateConfiguration={
            "type": "KNOWLEDGE_BASE",
            "knowledgeBaseConfiguration": {
                "knowledgeBaseId": KB_ID,
                "modelArn": MODEL_ARN,
                "retrievalConfiguration": {
                    "vectorSearchConfiguration": {
                        "numberOfResults": 5
                    }
                }
            }
        }
    )
    
    return response["output"]["text"]

def send_slack_notification(push_info, report, report_key):
    """Send Slack notification with push analysis"""
    try:
        # Truncate report for Slack (Slack has message limits)
        truncated_report = report[:2000] + "..." if len(report) > 2000 else report
        
        payload = {
            "text": f"🔍 Push Analysis Complete: {push_info['branch']} by {push_info['pusher']}",
            "attachments": [{
                "color": "#36a64f",
                "fields": [
                    {
                        "title": "Push Information",
                        "value": f"Branch: {push_info['branch']}\nPusher: {push_info['pusher']}\nCommits: {push_info['commits_count']}\nHead: {push_info['head_sha'][:8]}",
                        "short": True
                    },
                    {
                        "title": "Report Location",
                        "value": f"s3://{S3_BUCKET}/{report_key}",
                        "short": True
                    }
                ],
                "text": truncated_report
            }]
        }
        
        response = requests.post(SLACK_WEBHOOK_URL, json=payload)
        response.raise_for_status()
        print(f"✅ Slack notification sent: {response.status_code}")
        
    except Exception as e:
        print(f"❌ Failed to send Slack notification: {e}")

def cleanup_temp_files(repo_path):
    """Clean up temporary files"""
    try:
        parent_dir = os.path.dirname(repo_path)
        shutil.rmtree(parent_dir)
        print("✅ Temporary files cleaned up")
    except Exception as e:
        print(f"❌ Failed to cleanup temp files: {e}")
