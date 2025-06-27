# Style Frontend

This project is a React TypeScript application for the Generative Stylist service, providing a user interface for fashion style consultation and visualization.

## Prerequisites

- Node.js (v14 or higher)
- npm or yarn
- AWS Account with deployed backend services

## Project Structure

```
style-frontend/
├── src/
│   ├── assets/         # Static assets (images, icons)
│   ├── display/        # Display-related components
│   ├── locales/        # i18n translation files
│   ├── user/           # User-related components
│   ├── App.tsx         # Main application component
│   └── index.tsx       # Application entry point
├── public/             # Public static files
└── package.json        # Project dependencies and scripts
```

## Setup

1. Install dependencies:
```bash
npm install
```

2. Create a `.env` file in the root directory with the following content:
```env
REACT_APP_API_ENDPOINT=https://<your-api-gateway-id>.execute-api.<region>.amazonaws.com/prod/apis
REACT_APP_USER_AGREEMENT_ENDPOINT=https://<your-user-agreement-api-id>.execute-api.<region>.amazonaws.com/prod
REACT_APP_COGNITO_USER_POOL_ID=<your-user-pool-id>
REACT_APP_COGNITO_CLIENT_ID=<your-client-id>

Replace the placeholders with the actual endpoints and user pool related information from your backend deployment:
- `<your-api-gateway-id>`: The ID of your main API Gateway
- `<your-user-agreement-api-id>`: The ID of your User Agreement API Gateway
- `<your-user-pool-id>`: The ID of your Cognito User Pool (format: region_xxxxxxxxxxxxx)
- `<your-client-id>`: The Cognito App Client ID (format: xxxxxxxxxxxxxxxxxxxxx)
- `<region>`: Your AWS region (e.g., us-west-2)

To set main API Gateway endpoint in the .env file:

1. Go to AWS API Gateway Console and select 'APIs' from the left navigation menu
2. In the API list, search for 'GenerativeStylistApiGatewayStack'
3. Select the API and find the endpoint URL in the 'API endpoint' section
4. Copy the https://<your-api-gateway-id>.execute-api.<region>.amazonaws.com part from this URL and set it as REACT_APP_API_ENDPOINT
5. Add '/prod/apis' to the end of the URL

To set User Agreement API Gateway endpoint in the .env file:

1. Go to AWS API Gateway Console and select 'APIs' from the left navigation menu
2. In the API list, search for 'GenerativeStylistUserAgreementApi'
3. Select the API and find the endpoint URL in the 'API endpoint' section
4. Copy the https://<your-user-agreement-api-id>.execute-api.<region>.amazonaws.com part from this URL and set it as REACT_APP_USER_AGREEMENT_ENDPOINT
5. Add '/prod' to the end of the URL

For both endpoints, replace <region> with your AWS region (e.g., us-west-2)
```

To set Cognito values in the .env file:

1. Go to AWS Cognito Console and select 'User Pools' from the left navigation menu
2. In the user pool list, search for 'GenerativeStylistUserPool'
3. Once found, copy the Pool ID from the 'User pool overview' section and set it as `REACT_APP_COGNITO_USER_POOL_ID`
4. Navigate to the 'App integration' tab in the left menu
5. Scroll down to the 'App clients and analytics' section
6. Find 'GenerativeStylistClient' in the app clients list
7. Copy the Client ID and set it as `REACT_APP_COGNITO_CLIENT_ID`


## Available Scripts

- `npm start`: Runs the app in development mode
- `npm run build:dev`: Builds the app for development
- `npm run build:prod`: Builds the app for production
- `npm test`: Runs the test suite
- `npm run eject`: Ejects from Create React App

## Features

- User authentication with AWS Cognito
- Photo upload and personal style preferences input
- AI-powered fashion style generation
- Multiple style suggestions based on user preferences
- Multi-language support (i18n)
- User agreement management
- Style sharing capabilities

## Dependencies

Key dependencies include:
- AWS Amplify for AWS service integration
- React Query for data fetching
- i18next for internationalization
- Axios for HTTP requests
- React Router for navigation
- React Webcam for camera access

## Testing

The project includes Jest and React Testing Library for testing. Run tests with:
```bash
npm test
```

## Building for Production

To create a production build:
```bash
npm run build:prod
```

The build output will be in the `build` directory.

## Development

To start the development server:
```bash
npm start
```

The app will be available at `http://localhost:3000`.

## Contributing

1. Create a feature branch
2. Make your changes
3. Run tests
4. Submit a pull request

## License

This project is licensed under the MIT License.
