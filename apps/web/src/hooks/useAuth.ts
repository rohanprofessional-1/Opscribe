import { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';

export function useAuth() {
    const [user, setUser] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
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
