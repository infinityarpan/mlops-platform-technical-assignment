export const environment = {
  apiBase: '/api',
  authMode: 'oidc' as 'header' | 'oidc',
  keycloak: {
    issuer: 'http://localhost:8080/realms/mlops',
    clientId: 'mlops-ui',
    scope: 'openid profile email roles'
  }
};
