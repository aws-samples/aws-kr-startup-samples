import React from 'react';
import { Amplify } from 'aws-amplify';
import { HashRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import UserStart from './user/UserStart';
import UserPhoto from './user/UserPhoto';
import UserAsking from './user/UserAsking';
import UserFinish from './user/UserFinish';
import DisplayApp from './display/Display';
import { Authenticator, components } from '@aws-amplify/ui-react';
import '@aws-amplify/ui-react/styles.css';
import './App.css';

Amplify.configure({
  Auth: {
    Cognito: {
      userPoolId: process.env.REACT_APP_COGNITO_USER_POOL_ID,
      userPoolClientId: process.env.REACT_APP_COGNITO_CLIENT_ID,
    }
  }
});

const App = () => {
  return (
    <Authenticator>
      {({ signOut, user }) => (
        <Router>
          <Routes>
            <Route path="/" element={<Navigate to="/user/start" replace />} />
            <Route path="/user/start" element={<UserStart signOut={signOut} user={user} />} />
            <Route path="/user/ask" element={<UserAsking signOut={signOut} user={user} />} />
            <Route path="/user/photo" element={<UserPhoto signOut={signOut} user={user} />} />
            <Route path="/user/finish" element={<UserFinish/>} />
            <Route path="/display/:id" element={<DisplayApp />} />
          </Routes>
      </Router>
      )}
    </Authenticator>
  );
};

export default App;
