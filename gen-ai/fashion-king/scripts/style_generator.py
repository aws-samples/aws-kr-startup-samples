import boto3
import json
import argparse

# 테이블 이름과 사용할 모델
with open('../style-backend/cdk.context.json', 'r') as f:
    context = json.load(f)
TABLE_NAME = context['ddb_generative_stylist_fashion_style_table_name']
MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"
print("Table Name: ", TABLE_NAME)

# AWS clients
session = boto3.Session()  # profile_name 제거
dynamodb = session.resource('dynamodb')
table = dynamodb.Table(TABLE_NAME)
bedrock_runtime = session.client('bedrock-runtime', region_name="us-west-2")  # 리전 설정 주의

def print_table_info():
    table_desc = table.meta.client.describe_table(TableName=TABLE_NAME)
    print("Table Key Schema:", table_desc['Table']['KeySchema'])
    print("Table ARN:", table_desc['Table']['TableArn'])

def generate_styles_with_bedrock(theme, count, country):
    prompt = f"""
You are an expert fashion stylist.

Please create {count} unique style concepts based on the following theme: "{theme}".

For each style, provide:
- Style Name (short, catchy)
- Country ({country})
- Prompt (short visual description for generating an image)

Return the result in JSON array format like:
[
  {{"StyleName": "...", "Prompt": "...", "Country": "..."}},
  ...
]
Please write the StyleName in the local {country} language, and the prompt in English.
"""
    response = bedrock_runtime.invoke_model(
        modelId=MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=json.dumps({
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 4096,  # Claude 3 Sonnet의 최대 토큰 수는 4096입니다
            "anthropic_version": "bedrock-2023-05-31"
        })
    )

    response_body = json.loads(response['body'].read())
    model_message = response_body['content'][0]['text']
    print(model_message)
    try:
        styles = json.loads(model_message)
        if isinstance(styles, list):
            return styles
        else:
            print("응답이 예상한 JSON 배열이 아닙니다.")
            return []
    except Exception as e:
        print(f"JSON 파싱 에러: {e}")
        return []

def show_styles(styles):
    print("\n✨ 현재 스타일 목록:\n")
    for idx, style in enumerate(styles, 1):
        print(f"{idx}. {style['StyleName']} - {style['Prompt']}\n")

def edit_styles(styles):
    while True:
        show_styles(styles)
        choice = input("수정할 스타일 번호를 입력하세요 (완료하려면 'done'): ").strip()
        if choice.lower() == 'done':
            break

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(styles):
                new_name = input(f"새 스타일 이름을 입력하세요 (기존: {styles[idx]['StyleName']}): ").strip()
                new_prompt = input(f"새 프롬프트를 입력하세요 (기존: {styles[idx]['Prompt']}): ").strip()

                if new_name:
                    styles[idx]['StyleName'] = new_name
                if new_prompt:
                    styles[idx]['Prompt'] = new_prompt

                print("✅ 수정 완료!\n")
            else:
                print("⚠️ 잘못된 번호입니다.\n")
        except ValueError:
            print("⚠️ 숫자를 입력하세요.\n")

def confirm_or_edit(styles):
    while True:
        show_styles(styles)
        choice = input("이 스타일을 저장하시겠습니까? (yes / no): ").strip().lower()
        if choice == 'yes':
            return True
        elif choice == 'no':
            print("\n🛠️ 스타일을 수정합니다!\n")
            edit_styles(styles)
        else:
            print("⚠️ 'yes' 또는 'no'로 답변해주세요.\n")

def insert_styles(styles):
    print("\n🛠️ DynamoDB에 저장 중...\n")
    with table.batch_writer() as batch:
        for style in styles:
            item = {
                "StyleName": style['StyleName'],
                "Prompt": style['Prompt'],
                "Country": style['Country']
            }
            batch.put_item(Item=item)
    print(f"🎉 총 {len(styles)}개의 스타일이 성공적으로 추가되었습니다!")

def main():
    parser = argparse.ArgumentParser(description="Generate and insert styles using Bedrock Claude 3.5")
    parser.add_argument('--theme', type=str, required=True, help="Style theme (e.g., 'Indian traditional fashion')")
    parser.add_argument('--count', type=int, required=True, help="Number of styles to generate")
    parser.add_argument('--country', type=str, required=True, help="Country where this style is popular or originated from")
    args = parser.parse_args()

    print_table_info()

    styles = generate_styles_with_bedrock(args.theme, args.count, args.country)

    if not styles:
        print("스타일 생성 실패. 종료합니다.")
        return

    if confirm_or_edit(styles):
        insert_styles(styles)
    else:
        print("⛔ 저장을 취소했습니다.")

if __name__ == "__main__":
    main()