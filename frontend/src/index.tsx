import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import { configureAmplify } from './lib/amplify-config';

// Initialise AWS Amplify before the React tree mounts so that Auth calls
// made inside components (e.g. useAuth) have a valid configuration.
configureAmplify();

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
