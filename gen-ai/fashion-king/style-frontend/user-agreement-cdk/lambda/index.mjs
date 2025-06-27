import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { DynamoDBDocumentClient, UpdateCommand } from "@aws-sdk/lib-dynamodb";

const ddbClient = new DynamoDBClient({});
const ddbDocClient = DynamoDBDocumentClient.from(ddbClient);

export const handler = async (event) => {
  try {
    const requestBody = JSON.parse(event.body);

    console.log("request = "+JSON.stringify(requestBody));
    console.log("table = "+process.env.TABLE_NAME);

    const { id, name, agree, requestedAt, userId } = requestBody;

    if (!id || !name || agree === undefined || !requestedAt ) {
      return {
        statusCode: 400,
        body: JSON.stringify({ message: 'Missing required fields' }),
      };
    }
    
    const savedAt = new Date().toISOString();
    
    const params = {
      TableName: process.env.TABLE_NAME,
       Key: {
          id: id,
          savedAt: savedAt
      },
      UpdateExpression: 'SET #n = :name, #a = :agree, #d = :requestedAt, #u = :userId',
      ExpressionAttributeNames: {
        '#n': 'name',
        '#a': 'agree',
        '#d': 'requestedAt',
        '#u': 'userId'
      },
      ExpressionAttributeValues: {
        ':name': name,
        ':agree': agree,
        ':requestedAt': requestedAt,
        ':userId': userId
      },
    };

    const response = await ddbDocClient.send(new UpdateCommand(params));
    console.log(response);

    return {
      statusCode: 200,
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "GET,PUT,POST,DELETE,OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, Content-Length, X-Requested-With"
      },
      body: JSON.stringify({ message: 'Item updated successfully' }),
    };
  } catch (error) {
    console.error('Error:', error);
    return {
      statusCode: 500,
      body: JSON.stringify({ message: 'Internal server error' }),
    };
  }
};
