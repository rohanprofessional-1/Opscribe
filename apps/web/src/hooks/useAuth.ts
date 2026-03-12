import { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';

export function useAuth() {
    const [user, setUser] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // Check URL params for SSO callback (Auth0 redirects here with token)
        const params = new URLSearchParams(window.location.search);
        const ssoToken = params.get('token');
        const clientId = params.get('client_id');
        const clientName = params.get('client_name');
        const userEmail = params.get('user_email');
        const userName = params.get('user_name');

        if (ssoToken && clientId) {
            // SSO login successful — store credentials
            const ssoUser = {
                id: clientId,
                name: clientName || 'Unknown',
                email: userEmail,
                full_name: userName,
            };
            localStorage.setItem('opscribe_token', ssoToken);
            localStorage.setItem('opscribe_user', JSON.stringify(ssoUser));
            setUser(ssoUser);
            setLoading(false);

            // Clean up URL params so they don't persist on refresh
            window.history.replaceState({}, '', window.location.pathname);
            return;
        }

        // Otherwise, check localStorage for existing session
        const token = localStorage.getItem('opscribe_token');
        const storedUser = localStorage.getItem('opscribe_user');
        if (token && storedUser) {
            setUser(JSON.parse(storedUser));
        }
        setLoading(false);
    }, []);

    const login = useCallback(async (clientId: string) => {
        const res = await api.loginById(clientId);
        localStorage.setItem('opscribe_token', res.token.access_token);
        localStorage.setItem('opscribe_user', JSON.stringify(res.client));
        setUser(res.client);
        return res;
    }, []);

    const setup = useCallback(async (data: any) => {
        const res = await api.setupAccount(data);
        localStorage.setItem('opscribe_token', res.token.access_token);
        localStorage.setItem('opscribe_user', JSON.stringify(res.client));
        setUser(res.client);
        return res;
    }, []);

    const logout = useCallback(() => {
        localStorage.removeItem('opscribe_token');
        localStorage.removeItem('opscribe_user');
        setUser(null);
        window.location.href = '/login';
    }, []);

    return {
        user,
        loading,
        login,
        setup,
        logout,
        isAuthenticated: !!user,
    };
}
