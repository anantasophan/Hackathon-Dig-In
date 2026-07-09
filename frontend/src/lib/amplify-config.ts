import { Amplify } from 'aws-amplify';

export function configureAmplify(): void {
  const userPoolId = process.env.REACT_APP_USER_POOL_ID ?? '';
  const userPoolClientId = process.env.REACT_APP_USER_POOL_CLIENT_ID ?? '';
  Amplify.configure({
    Auth: { Cognito: { userPoolId, userPoolClientId, loginWith: { username: true } } },
  });
}
