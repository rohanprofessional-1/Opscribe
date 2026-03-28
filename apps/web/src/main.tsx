import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { Auth0Provider } from '@auth0/auth0-react'
import './index.css'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Auth0Provider
      domain="dev-xuzgmpozdykvxgyp.us.auth0.com"
      clientId="BVQBker56bNozDLWvYuJRCMzFzzj1oZZ"
      authorizationParams={{
        redirect_uri: window.location.origin,
        audience: "https://dev-xuzgmpozdykvxgyp.us.auth0.com/api/v2/"
      }}
    >
      <App />
    </Auth0Provider>
  </StrictMode>,
)

