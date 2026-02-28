import { useEffect, useState } from 'react';
import { Outlet, useNavigate } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import api from '../api';
import { Bell, Search } from 'lucide-react';

const AdminLayout = () => {
    const navigate = useNavigate();
    const [user, setUser] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const checkAuth = async () => {
            const token = localStorage.getItem('admin_token');
            if (!token) {
                navigate('/login');
                return;
            }
            try {
                const res = await api.get('/users/me');
                const u = res.data;
                if (!u.is_superuser && u.role !== 'college_admin') {
                    alert('Access Denied: Admin privileges required.');
                    localStorage.removeItem('admin_token');
                    navigate('/login');
                    return;
                }
                setUser(u);
            } catch (err) {
                localStorage.removeItem('admin_token');
                navigate('/login');
            } finally {
                setLoading(false);
            }
        };
        checkAuth();
    }, [navigate]);

    if (loading) {
        return (
            <div className="min-h-screen bg-slate-950 flex items-center justify-center">
                <div className="w-12 h-12 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-slate-950 flex text-slate-200">
            <Sidebar />
            <div className="flex-1 flex flex-col">
                <header className="h-20 border-b border-slate-800 flex items-center justify-between px-8 bg-slate-950/50 backdrop-blur-md sticky top-0 z-10">
                    <div className="flex items-center gap-4 flex-1">
                        <div className="relative w-96">
                            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                            <input
                                placeholder="Search database..."
                                className="w-full bg-slate-900/50 border border-slate-800 rounded-full pl-10 pr-4 py-2 outline-none focus:border-indigo-500 transition-all text-sm"
                            />
                        </div>
                    </div>

                    <div className="flex items-center gap-6">
                        <button className="bg-slate-900 p-2 rounded-full border border-slate-800 relative hover:bg-slate-800 transition-colors">
                            <Bell className="w-5 h-5 text-slate-400" />
                            <span className="absolute top-1 right-1 w-2.5 h-2.5 bg-red-500 rounded-full border-2 border-slate-950"></span>
                        </button>
                        <div className="flex items-center gap-3 pl-6 border-l border-slate-800">
                            <div className="text-right">
                                <p className="text-sm font-semibold text-white">{user?.full_name}</p>
                                <p className="text-xs text-slate-500 capitalize">{user?.is_superuser ? 'Super Admin' : user?.role?.replace('_', ' ') ?? 'Admin'}</p>
                            </div>
                            <div className="w-10 h-10 rounded-full bg-linear-to-tr from-indigo-600 to-pink-500 p-0.5">
                                <div className="w-full h-full rounded-full bg-slate-900 flex items-center justify-center font-bold text-sm">
                                    {user?.full_name?.[0]}
                                </div>
                            </div>
                        </div>
                    </div>
                </header>

                <main className="flex-1 p-8">
                    <Outlet context={{ user }} />
                </main>
            </div>
        </div>
    );
};

export default AdminLayout;
