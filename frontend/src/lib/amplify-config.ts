/**
 * AWS Amplify configuration for Cognito authentication.
 *
 * Reads connection parameters from environment variables so no secrets
 * are hard-coded in source.  Call `configureAmplify()` once at app
 * start-up (before rendering) to initialise the Amplify library.
 */

import { Amplify } from 'aws-amplify';

/**
 * Configure AWS Amplify with Cognito User Pool settings sourced from
 * `REACT_APP_*` environment variables.
 *
 * Must be called before any Auth operation or component that depends on
 * Amplify (e.g. before ReactDOM.render / createRoot).
 */
export function configureAmplify(): void {
  const userPoolId = process.env.REACT_APP_USER_POOL_ID ?? '';
  const userPoolClientId = process.env.REACT_APP_USER_POOL_CLIENT_ID ?? '';

  Amplify.configure({
    Auth: {
      Cognito: {
        userPoolId,
        userPoolClientId,
        loginWith: {
          username: true,
        },
      },
    },
  });
}
