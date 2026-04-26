import React, { useEffect, useState } from 'react';
import client, { apiEvents } from '../api/client';
import Card from '../components/Card';
import { Link } from 'react-router-dom';

const Blueprint = () => {
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [apiLogs, setApiLogs] = useState([]);
  const [lastSynced, setLastSynced] = useState(null);
  const [isOps, setIsOps] = useState(localStorage.getItem('role') === 'ops');

  const fetchData = async () => {
    if (!isOps) {
      setLoading(false);
      return;
    }
    try {
      const analyticsRes = await client.get('/api/v1/ops/analytics');
      setAnalytics(analyticsRes.data);
      setLastSynced(new Date().toLocaleTimeString());
    } catch (error) {
      console.error('Blueprint fetch error:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();

    // Subscribe to live API logs
    const handleRequest = (e) => {
      setApiLogs(prev => [{ ...e.detail, type: 'REQUEST' }, ...prev].slice(0, 100));
    };
    const handleResponse = (e) => {
      setApiLogs(prev => [{ ...e.detail, type: 'RESPONSE' }, ...prev].slice(0, 100));
    };

    apiEvents.addEventListener('request', handleRequest);
    apiEvents.addEventListener('response', handleResponse);

    const interval = setInterval(fetchData, 10000);
    return () => {
      clearInterval(interval);
      apiEvents.removeEventListener('request', handleRequest);
      apiEvents.removeEventListener('response', handleResponse);
    };
  }, [isOps]);

  const coreAgents = [
    { id: 'C1', name: 'Workflow Engine', role: 'Orchestrator', desc: 'Authoritative controller for all state transitions. Enforces deterministic logic and atomicity.' },
    { id: 'C2', name: 'Routing Service', role: 'Traffic Manager', desc: 'Analyzes lead readiness and shoots data to determine the optimal processing path.' },
    { id: 'C3', name: 'Profile Service', role: 'Identity Agent', desc: 'Enriches client data and manages high-fidelity production profiles across the lifecycle.' },
    { id: 'C4', name: 'Followup Service', role: 'Retention Agent', desc: 'Manages automated re-engagement for leads requiring missing production details.' },
    { id: 'C5', name: 'Analytics Service', role: 'Insights Agent', desc: 'Aggregates global system metrics and generates operational snapshots for the dashboard.' }
  ];

  const aiAgents = [
    { id: 'A1', name: 'Intake Service', role: 'Parsing LLM', desc: 'Translates unstructured inquiry text into structured JSON production specs.' },
    { id: 'A2', name: 'Readiness Service', role: 'Scoring LLM', desc: 'Evaluates the quality and completeness of incoming leads to prevent pipeline noise.' },
    { id: 'A3', name: 'Matching Service', role: 'Discovery LLM', desc: 'Uses vector embeddings to find perfect locations matching complex production requirements.' },
    { id: 'A4', name: 'Permit Service', role: 'Legal LLM', desc: 'Generates and validates filming permit documentation for local authorities.' },
    { id: 'A5', name: 'Comm Service', role: 'Omnichannel Agent', desc: 'Orchestrates template-based messaging via Email and WhatsApp at key milestones.' },
    { id: 'A6', name: 'Nurturing Service', role: 'Engagement LLM', desc: 'Generates personalized production advice to convert stale or inactive leads.' }
  ];

  return (
    <div className="min-h-screen bg-slate-50 text-slate-600 font-mono text-[11px] selection:bg-primary/20 selection:text-primary leading-relaxed">
      {/* Schematic Header */}
      <div className="max-w-7xl mx-auto px-8 py-12 border-b border-slate-200 bg-white shadow-sm">
        <div className="flex justify-between items-center">
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <div className="w-4 h-4 bg-primary rounded-sm rotate-45" />
              <h1 className="text-2xl font-black text-slate-900 tracking-[0.4em] uppercase">Architecture Blueprint</h1>
            </div>
            <p className="text-[10px] text-primary font-bold uppercase tracking-widest flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-primary" />
              Technical Specification & Live Telemetry
            </p>
          </div>
            <div className="text-right">
              <p className="text-[8px] font-black text-slate-400 uppercase tracking-widest mb-1">Developer Attribution</p>
              <p className="text-[11px] font-black text-primary uppercase mb-3">Varun Dronamraju</p>
              <p className="text-[8px] font-black text-slate-400 uppercase tracking-widest mb-1">System Time (UTC)</p>
              <p className="text-[11px] font-black text-slate-900 uppercase">
                {new Date().toISOString().split('T')[1].split('.')[0]}
              </p>
            </div>
            {!isOps && (
              <Link to="/login" className="px-5 py-2 bg-slate-900 text-white text-[9px] font-black uppercase tracking-[0.2em] rounded-full hover:bg-primary transition-all">
                Elevate Authorization
              </Link>
            )}
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-8 py-16 grid grid-cols-1 lg:grid-cols-12 gap-16">
        
        {/* Schematic Columns */}
        <div className="lg:col-span-8 space-y-24">
          
          {/* Section: Agents (Static) */}
          <section className="space-y-12">
            <div className="flex items-center justify-between">
              <h2 className="text-[10px] font-black text-slate-900 uppercase tracking-[0.4em] flex items-center gap-3">
                <span className="w-2 h-[1px] bg-slate-900" />
                01. Agent Ecosystem (Static Spec)
              </h2>
              <span className="text-[8px] font-bold text-slate-400 uppercase tracking-widest">Reference Object</span>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-12 gap-y-16">
              <div className="space-y-8">
                <div className="pb-4 border-b border-slate-200">
                  <h3 className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Core (C-Series)</h3>
                </div>
                <div className="space-y-6">
                  {coreAgents.map(agent => (
                    <div key={agent.id} className="relative pl-6 border-l border-slate-200 group">
                      <div className="absolute left-[-4.5px] top-0 w-2 h-2 border border-slate-200 bg-white group-hover:bg-primary transition-colors" />
                      <div className="space-y-1">
                        <p className="text-slate-900 font-black uppercase tracking-tight">{agent.id}: {agent.name}</p>
                        <p className="text-primary text-[9px] font-bold uppercase tracking-tighter">{agent.role}</p>
                        <p className="text-slate-500 text-[10px] leading-snug">{agent.desc}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="space-y-8">
                <div className="pb-4 border-b border-slate-200">
                  <h3 className="text-[9px] font-black text-slate-400 uppercase tracking-widest">AI Services (A-Series)</h3>
                </div>
                <div className="space-y-6">
                  {aiAgents.map(agent => (
                    <div key={agent.id} className="relative pl-6 border-l border-slate-200 group">
                      <div className="absolute left-[-4.5px] top-0 w-2 h-2 border border-slate-200 bg-white group-hover:bg-primary transition-colors" />
                      <div className="space-y-1">
                        <p className="text-slate-900 font-black uppercase tracking-tight">{agent.id}: {agent.name}</p>
                        <p className="text-primary text-[9px] font-bold uppercase tracking-tighter">{agent.role}</p>
                        <p className="text-slate-500 text-[10px] leading-snug">{agent.desc}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </section>

          {/* Section: Workflows (Static) */}
          <section className="space-y-12">
            <h2 className="text-[10px] font-black text-slate-900 uppercase tracking-[0.4em] flex items-center gap-3">
              <span className="w-2 h-[1px] bg-slate-900" />
              02. Execution Workflows (Static Spec)
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <div className="p-8 bg-white border border-slate-200 rounded-3xl space-y-6 shadow-sm">
                <h4 className="text-[10px] font-black text-slate-900 uppercase tracking-widest border-b border-slate-50 pb-2">Intake Lifecycle</h4>
                <div className="space-y-4 text-slate-400">
                  <p>01. <span className="text-slate-900">Submission</span> → API Gateway</p>
                  <p>02. <span className="text-slate-900">A1 Agent</span> → Context Parsing</p>
                  <p>03. <span className="text-slate-900">A2 Agent</span> → Readiness Scoring</p>
                  <p>04. <span className="text-slate-900">C2 Agent</span> → Pipeline Routing</p>
                  <p>05. <span className="text-slate-900">C1 Engine</span> → Atomic Commit</p>
                </div>
              </div>
              <div className="p-8 bg-white border border-slate-200 rounded-3xl space-y-6 shadow-sm">
                <h4 className="text-[10px] font-black text-slate-900 uppercase tracking-widest border-b border-slate-50 pb-2">Booking Lifecycle</h4>
                <div className="space-y-4 text-slate-400">
                  <p>01. <span className="text-slate-900">Ops Override</span> → State Transition</p>
                  <p>02. <span className="text-slate-900">Entity Creation</span> → Booking Table</p>
                  <p>03. <span className="text-slate-900">A4 Agent</span> → Permit Generation</p>
                  <p>04. <span className="text-slate-900">A5 Agent</span> → Automated Comm</p>
                  <p>05. <span className="text-slate-900">C1 Engine</span> → Verification Sync</p>
                </div>
              </div>
            </div>
          {/* Section: Context Visibility (Static Reference) */}
          <section className="space-y-8">
            <h2 className="text-[10px] font-black text-slate-900 uppercase tracking-[0.4em] flex items-center gap-3">
              <span className="w-2 h-[1px] bg-slate-900" />
              04. Inquiry Context Schema
            </h2>
            <div className="bg-slate-900 rounded-3xl p-8 font-mono text-[10px] text-primary/80 overflow-hidden shadow-xl border border-slate-800">
              <p className="text-slate-500 mb-4 tracking-widest uppercase text-[8px] font-black">Raw Data Sample: Location-Based Inquiry</p>
              <pre className="custom-scrollbar overflow-x-auto">
{`{
  "context": {
    "type": "location",
    "data": {
      "id": "loc_7721",
      "name": "Brutalist Penthouse",
      "area": "Shoreditch, London",
      "crew_capacity": 45,
      "price_per_day": 2400
    }
  },
  "shoot_type": "Commercial",
  "requirements": "Need high ceilings and raw concrete textures..."
}`}
              </pre>
            </div>
          </section>

          {/* Section: Future Capabilities */}
          <section className="space-y-8 pb-20">
            <h2 className="text-[10px] font-black text-slate-900 uppercase tracking-[0.4em] flex items-center gap-3">
              <span className="w-2 h-[1px] bg-slate-900" />
              05. Roadmap & Scaling
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-12 gap-y-6 text-[10px] text-slate-500 font-bold uppercase tracking-widest">
              <ul className="space-y-3">
                <li className="flex items-center gap-3">
                  <span className="w-1 h-1 bg-primary rounded-full" />
                  Real-time Slack / Discord Notifications
                </li>
                <li className="flex items-center gap-3">
                  <span className="w-1 h-1 bg-primary rounded-full" />
                  Automated A3 Embedding Pipeline
                </li>
                <li className="flex items-center gap-3">
                  <span className="w-1 h-1 bg-primary rounded-full" />
                  Predictive Lead Scoring (A2 v2)
                </li>
              </ul>
              <ul className="space-y-3">
                <li className="flex items-center gap-3">
                  <span className="w-1 h-1 bg-primary rounded-full" />
                  Dynamic Pricing Intelligence
                </li>
                <li className="flex items-center gap-3">
                  <span className="w-1 h-1 bg-primary rounded-full" />
                  Automated Matching → Direct Booking
                </li>
                <li className="flex items-center gap-3">
                  <span className="w-1 h-1 bg-primary rounded-full" />
                  Client-Ops Real-time Collaboration
                </li>
              </ul>
            </div>
          </section>
        </div>

        {/* Live Telemetry Panel */}
        <div className="lg:col-span-4 space-y-12">
          
          {/* Live Metrics */}
          <section className="space-y-6">
            <div className="flex justify-between items-end border-l-2 border-primary pl-4">
              <h2 className="text-[10px] font-black text-slate-900 uppercase tracking-[0.3em]">Live System Telemetry</h2>
              <span className="text-[8px] font-black text-primary animate-pulse uppercase">Syncing...</span>
            </div>
            
            {isOps ? (
              <div className="space-y-4">
                <Card className="!bg-white border-slate-200 !p-8 space-y-2 relative overflow-hidden group">
                  <div className="absolute top-0 right-0 p-2 opacity-10 group-hover:opacity-100 transition-opacity">
                    <p className="text-[8px] font-black text-slate-400 uppercase">Snapshot: {lastSynced}</p>
                  </div>
                  <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Total Pipeline Volume</p>
                  <p className="text-4xl font-black text-slate-900">{analytics?.total_leads || 0}</p>
                </Card>
                <Card className="!bg-white border-slate-200 !p-8 space-y-2 relative overflow-hidden group">
                  <div className="absolute top-0 right-0 p-2 opacity-10 group-hover:opacity-100 transition-opacity">
                    <p className="text-[8px] font-black text-slate-400 uppercase">Snapshot: {lastSynced}</p>
                  </div>
                  <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Global Conversion Rate</p>
                  <p className="text-4xl font-black text-slate-900">{(analytics?.conversion_rate * 100 || 0).toFixed(1)}%</p>
                </Card>
                <div className="text-center">
                  <p className="text-[8px] font-black text-slate-300 uppercase tracking-widest">
                    Telemetry Last Verified: {lastSynced}
                  </p>
                </div>
              </div>
            ) : (
              <div className="p-8 border border-primary/20 bg-primary/5 rounded-[40px] text-center space-y-4">
                <p className="text-[10px] text-primary font-bold uppercase tracking-widest">Restricted Telemetry</p>
                <p className="text-[10px] text-slate-400 leading-relaxed">Live pipeline metrics are restricted to Operational Admins. Authenticate to view real-time data flow.</p>
                <Link to="/login" className="inline-block px-8 py-3 bg-slate-900 text-white text-[9px] font-black uppercase tracking-[0.2em] rounded-full">System Login</Link>
              </div>
            )}
          </section>

          {/* API Event Stream */}
          <section className="space-y-6">
            <h2 className="text-[10px] font-black text-slate-900 uppercase tracking-[0.3em] pl-4 border-l-2 border-slate-200">Global API Event Log</h2>
            <div className="bg-slate-900 rounded-[32px] h-[500px] overflow-y-auto no-scrollbar p-8 shadow-2xl">
              <div className="space-y-6">
                {apiLogs.length === 0 && (
                  <div className="flex flex-col items-center justify-center py-20 text-slate-700 space-y-4">
                    <div className="w-8 h-8 border-2 border-slate-800 border-t-primary rounded-full animate-spin" />
                    <p className="text-[9px] font-black uppercase tracking-widest italic text-center">Awaiting System Pulse...</p>
                  </div>
                )}
                {apiLogs.map((log, i) => (
                  <div key={i} className="space-y-2 border-b border-slate-800 pb-5 last:border-0 group">
                    <div className="flex justify-between items-center text-[8px] font-black uppercase tracking-widest">
                      <span className={`${log.type === 'REQUEST' ? 'text-blue-400' : 'text-primary'}`}>
                        {log.type}
                      </span>
                      <span className="text-slate-600 group-hover:text-slate-400 transition-colors">{log.timestamp}</span>
                    </div>
                    <div className="flex gap-3 items-center">
                      <span className={`px-2 py-0.5 rounded-full text-[8px] font-black border ${
                        log.status === 200 || log.status === 202 ? 'border-primary/40 text-primary bg-primary/5' : 
                        log.status === 'FAIL' || log.status >= 400 ? 'border-red-500/40 text-red-400 bg-red-500/5' :
                        'border-blue-500/40 text-blue-400 bg-blue-500/5'
                      }`}>
                        {log.status || log.method}
                      </span>
                      <p className="text-slate-400 truncate tracking-tighter text-[10px]">{log.url}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </section>

        </div>
      </div>
    </div>
  );
};

export default Blueprint;
