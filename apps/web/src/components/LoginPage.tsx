import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { Globe, User, LogIn } from 'lucide-react';
import { api } from '../api/client';

const LoginPage: React.FC = () => {
    const [clientId, setClientId] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();
    const { login } = useAuth();

    const handleClientIdLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError('');
        try {
            await login(clientId);
            navigate('/dashboard');
        } catch (err: any) {
            setError(err.message || 'Invalid Client ID');
        } finally {
            setLoading(false);
        }
    };

    const handleSSOLogin = () => {
        window.location.href = api.getSSOLoginUrl();
    };

    return (
        <div className="min-h-screen bg-slate-900 text-white flex items-center justify-center p-6">
            <div className="w-full max-w-lg bg-slate-800 rounded-3xl p-10 border border-slate-700 shadow-2xl">
                <div className="mb-10 text-center">
                    <h2 className="text-3xl font-bold mb-2">Welcome back</h2>
                    <p className="text-slate-400">Sign in to your Opscribe account.</p>
                </div>

                <button
                    onClick={handleSSOLogin}
                    className="w-full flex items-center justify-center gap-3 py-4 bg-white text-slate-900 hover:bg-slate-100 rounded-xl font-bold transition-all mb-8 shadow-lg shadow-white/5"
                >
                    <Globe size={20} />
                    Sign in with Company SSO
                </button>

                <div className="relative mb-8">
                    <div className="absolute inset-0 flex items-center">
                        <div className="w-full border-t border-slate-700"></div>
                    </div>
                    <div className="relative flex justify-center text-sm">
                        <span className="px-4 bg-slate-800 text-slate-500">Or use Client ID</span>
                    </div>
                </div>

                <form onSubmit={handleClientIdLogin} className="space-y-6">
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-slate-300">Client ID</label>
                        <div className="relative">
                            <User className="absolute left-3 top-3.5 text-slate-500" size={18} />
                            <input
                                type="text"
                                required
                                className="w-full bg-slate-900 border border-slate-700 rounded-xl py-3 pl-10 pr-4 focus:ring-2 focus:ring-blue-500 outline-none"
                                placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                                value={clientId}
                                onChange={(e) => setClientId(e.target.value)}
                            />
                        </div>
                    </div>

                    {error && <div className="text-red-400 text-sm mt-4 p-3 bg-red-900/20 rounded-lg">{error}</div>}

                    <button
                        type="submit"
                        disabled={loading}
                        className="w-full flex items-center justify-center gap-2 py-3 bg-slate-700 hover:bg-slate-600 rounded-xl font-bold transition-all disabled:opacity-50"
                    >
                        <LogIn size={20} />
                        {loading ? 'Signing in...' : 'Sign In'}
                    </button>
                </form>

                <p className="mt-10 text-center text-slate-500 text-sm">
                    Don't have an account? <button onClick={() => navigate('/setup')} className="text-blue-400 hover:underline">Create one here</button>
                </p>
            </div>
        </div>
    );
};

export default LoginPage;
