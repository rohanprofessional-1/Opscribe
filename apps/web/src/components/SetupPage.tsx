import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { User, Building, Globe, ArrowRight } from 'lucide-react';

const SetupPage: React.FC = () => {
    const [formData, setFormData] = useState({
        client_name: '',
        user_full_name: '',
        user_email: '',
        sso_domain: '',
    });
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();
    const { setup } = useAuth();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError('');
        try {
            await setup(formData);
            navigate('/dashboard');
        } catch (err: any) {
            setError(err.message || 'Failed to create account');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-slate-900 text-white flex items-center justify-center p-6">
            <div className="w-full max-w-lg bg-slate-800 rounded-3xl p-10 border border-slate-700 shadow-2xl">
                <div className="mb-8">
                    <h2 className="text-3xl font-bold mb-2">Create your account</h2>
                    <p className="text-slate-400">Set up your workspace and start designing.</p>
                </div>

                <form onSubmit={handleSubmit} className="space-y-6">
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-slate-300">Company Name</label>
                        <div className="relative">
                            <Building className="absolute left-3 top-3.5 text-slate-500" size={18} />
                            <input
                                type="text"
                                required
                                className="w-full bg-slate-900 border border-slate-700 rounded-xl py-3 pl-10 pr-4 focus:ring-2 focus:ring-blue-500 outline-none"
                                placeholder="Acme Corp"
                                value={formData.client_name}
                                onChange={(e) => setFormData({ ...formData, client_name: e.target.value })}
                            />
                        </div>
                    </div>

                    <div className="space-y-2">
                        <label className="text-sm font-medium text-slate-300">Full Name</label>
                        <div className="relative">
                            <User className="absolute left-3 top-3.5 text-slate-500" size={18} />
                            <input
                                type="text"
                                required
                                className="w-full bg-slate-900 border border-slate-700 rounded-xl py-3 pl-10 pr-4 focus:ring-2 focus:ring-blue-500 outline-none"
                                placeholder="John Doe"
                                value={formData.user_full_name}
                                onChange={(e) => setFormData({ ...formData, user_full_name: e.target.value })}
                            />
                        </div>
                    </div>

                    <div className="space-y-2">
                        <label className="text-sm font-medium text-slate-300">Work Email</label>
                        <div className="relative">
                            <span className="absolute left-3 top-3.5 text-slate-500 font-bold">@</span>
                            <input
                                type="email"
                                required
                                className="w-full bg-slate-900 border border-slate-700 rounded-xl py-3 pl-10 pr-4 focus:ring-2 focus:ring-blue-500 outline-none"
                                placeholder="john@example.com"
                                value={formData.user_email}
                                onChange={(e) => setFormData({ ...formData, user_email: e.target.value })}
                            />
                        </div>
                    </div>

                    <div className="space-y-2">
                        <label className="text-sm font-medium text-slate-300">SSO Domain (Optional)</label>
                        <div className="relative">
                            <Globe className="absolute left-3 top-3.5 text-slate-500" size={18} />
                            <input
                                type="text"
                                className="w-full bg-slate-900 border border-slate-700 rounded-xl py-3 pl-10 pr-4 focus:ring-2 focus:ring-blue-500 outline-none"
                                placeholder="example.com"
                                value={formData.sso_domain}
                                onChange={(e) => setFormData({ ...formData, sso_domain: e.target.value })}
                            />
                        </div>
                    </div>

                    {error && <div className="text-red-400 text-sm mt-4 p-3 bg-red-900/20 rounded-lg">{error}</div>}

                    <button
                        type="submit"
                        disabled={loading}
                        className="w-full flex items-center justify-center gap-2 py-3 bg-blue-600 hover:bg-blue-500 rounded-xl font-bold transition-all mt-4 disabled:opacity-50"
                    >
                        {loading ? 'Creating Account...' : 'Continue'}
                        <ArrowRight size={20} />
                    </button>
                </form>

                <p className="mt-8 text-center text-slate-500 text-sm">
                    Already have an account? <button onClick={() => navigate('/login')} className="text-blue-400 hover:underline">Log in</button>
                </p>
            </div>
        </div>
    );
};

export default SetupPage;
