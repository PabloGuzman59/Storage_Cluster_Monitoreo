import { useState, useEffect } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export default function NodeHistory({ client_id, region, onClose }) {
  const [shortHistory, setShortHistory] = useState([]);
  const [longHistory, setLongHistory] = useState([]);

  useEffect(() => {
    setShortHistory([]);
    setLongHistory([]);
    const fetchHistory = () => {
      fetch(`/api/node/${client_id}/history?limit=5`)
        .then(res => res.json())
        .then(data => {
          const formattedData = data.reverse().map(item => ({
            ...item,
            hora: new Date(item.reported_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'})
          }));
          
          setShortHistory(formattedData);

          setLongHistory(prev => {
            if (prev.length === 0) {
              return [formattedData[formattedData.length - 1]];
            } else {
              const combined = [...prev];
              formattedData.forEach(newItem => {
                if (!combined.find(x => x.reported_at === newItem.reported_at)) {
                  combined.push(newItem);
                }
              });
              return combined;
            }
          });
        });
    };

    fetchHistory();
    const interval = setInterval(fetchHistory, 10000);
    return () => clearInterval(interval);
  }, [client_id]);

  const currentData = shortHistory.length > 0 ? shortHistory[shortHistory.length - 1] : {};
  const percent = currentData.utilization || 0;
  const radius = 45;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (percent / 100) * circumference;
  const gaugeColor = percent > 80 ? '#ff003c' : percent > 60 ? '#ffea00' : '#00f3ff';

  return (
    <>
      <style>
        {`
          @keyframes slideInRight {
            0% { transform: translateX(100%); opacity: 0; }
            100% { transform: translateX(0); opacity: 1; }
          }
          @keyframes smoothSlideIn {
            0% { opacity: 0; transform: translateY(-10px); background-color: rgba(0, 243, 255, 0.15); }
            100% { opacity: 1; transform: translateY(0); background-color: transparent; }
          }
          .panel-suave {
            animation: slideInRight 0.4s cubic-bezier(0.25, 1, 0.5, 1) forwards;
          }
          .animate-row {
            animation: smoothSlideIn 0.8s cubic-bezier(0.25, 1, 0.5, 1) forwards;
          }
          .no-scrollbar::-webkit-scrollbar { display: none; }
          .no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
        `}
      </style>

      <div className="panel-suave no-scrollbar" style={{ 
        position: 'fixed', top: 0, right: 0, width: '600px', height: '100vh', 
        background: 'rgba(10, 10, 15, 0.95)', backdropFilter: 'blur(20px)', WebkitBackdropFilter: 'blur(20px)',
        borderLeft: '1px solid rgba(0, 243, 255, 0.2)', boxShadow: '-10px 0 40px rgba(0,0,0,0.9)', 
        padding: '30px 40px', zIndex: 1000, overflowY: 'auto', color: 'white',
        display: 'flex', flexDirection: 'column'
      }}>
        
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '5px' }}>
          <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: '28px', cursor: 'pointer', color: '#a1a1aa', transition: 'color 0.2s', padding: 0, lineHeight: 1 }} onMouseEnter={(e)=>e.target.style.color='white'} onMouseLeave={(e)=>e.target.style.color='#a1a1aa'}>✖</button>
        </div>
        
        <h2 style={{ color: '#00f3ff', margin: '0 0 5px 0', textShadow: '0 0 10px rgba(0,243,255,0.4)', letterSpacing: '1px' }}>{region.toUpperCase()} // LINK</h2>
        
        <p style={{ color: '#a1a1aa', fontSize: '12px', marginTop: '20px', marginBottom: '15px', letterSpacing: '2px' }}>ESTADO ACTUAL DEL DISCO</p>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '40px', marginBottom: '30px', background: 'rgba(0,0,0,0.3)', padding: '20px 30px', borderRadius: '15px', border: '1px solid rgba(255,255,255,0.05)' }}>
          <div style={{ position: 'relative', width: '100px', height: '100px' }}>
            <svg width="100" height="100" style={{ transform: 'rotate(-90deg)' }}>
              <circle cx="50" cy="50" r={radius} stroke="rgba(255,255,255,0.1)" strokeWidth="8" fill="none" />
              <circle 
                cx="50" cy="50" r={radius} 
                stroke={gaugeColor} 
                strokeWidth="8" 
                fill="none" 
                strokeDasharray={circumference} 
                strokeDashoffset={strokeDashoffset}
                strokeLinecap="round"
                style={{ transition: 'stroke-dashoffset 1s ease-in-out, stroke 1s ease', filter: `drop-shadow(0 0 6px ${gaugeColor})` }}
              />
            </svg>
            <div style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <span style={{ fontSize: '22px', fontWeight: 'bold', color: 'white', textShadow: `0 0 10px ${gaugeColor}` }}>{percent}%</span>
            </div>
          </div>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div style={{ color: '#a1a1aa', fontSize: '12px', letterSpacing: '1px' }}>TOTAL: <strong style={{ color: 'white', fontSize: '16px', marginLeft: '5px' }}>{currentData.total_gb || 0} GB</strong></div>
            <div style={{ color: '#a1a1aa', fontSize: '12px', letterSpacing: '1px' }}>USADO: <strong style={{ color: gaugeColor, fontSize: '16px', marginLeft: '5px', textShadow: `0 0 5px ${gaugeColor}80` }}>{currentData.used_gb || 0} GB</strong></div>
            <div style={{ color: '#a1a1aa', fontSize: '12px', letterSpacing: '1px' }}>LIBRE: <strong style={{ color: 'white', fontSize: '16px', marginLeft: '5px' }}>{currentData.free_gb || 0} GB</strong></div>
          </div>
        </div>

        <p style={{ color: '#00f3ff', fontSize: '12px', marginBottom: '10px', letterSpacing: '2px', textShadow: '0 0 5px rgba(0,243,255,0.4)' }}>HISTORIAL ACUMULADO DESDE CONEXIÓN</p>
        <div style={{ height: '200px', marginBottom: '30px', background: 'rgba(0,0,0,0.3)', borderRadius: '12px', padding: '10px', border: '1px solid rgba(255,255,255,0.05)' }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={longHistory}>
              <defs>
                <linearGradient id="colorUso" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#00f3ff" stopOpacity={0.6}/>
                  <stop offset="95%" stopColor="#00f3ff" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="hora" tick={{fontSize: 10, fill: '#64748b'}} stroke="rgba(255,255,255,0.1)" />
              <YAxis domain={[0, 100]} tick={{fontSize: 10, fill: '#64748b'}} stroke="rgba(255,255,255,0.1)" unit="%" />
              <Tooltip contentStyle={{ backgroundColor: 'rgba(0,0,0,0.9)', border: '1px solid #00f3ff', color: 'white', borderRadius: '8px', boxShadow: '0 0 15px rgba(0,243,255,0.3)' }} itemStyle={{ color: '#00f3ff', fontWeight: 'bold' }} />
              <Area 
                type="monotone" 
                dataKey="utilization" 
                stroke="#00f3ff" 
                strokeWidth={3} 
                fillOpacity={1} 
                fill="url(#colorUso)" 
                isAnimationActive={true}
                animationDuration={500}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div style={{ flexGrow: 1, marginBottom: '20px' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
            <thead>
              <tr style={{ color: '#64748b', textAlign: 'left', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
                <th style={{ padding: '10px', letterSpacing: '1px' }}>HORA</th>
                <th style={{ padding: '10px', letterSpacing: '1px' }}>USADO (GB)</th>
                <th style={{ padding: '10px', letterSpacing: '1px' }}>IOPS</th>
              </tr>
            </thead>
            <tbody>
              {shortHistory.slice().reverse().map((row) => (
                <tr key={row.reported_at} className="animate-row" style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                  <td style={{ padding: '10px', color: '#a1a1aa' }}>{row.hora}</td>
                  <td style={{ padding: '10px', fontWeight: 'bold', color: 'white' }}>{row.used_gb}</td>
                  <td style={{ padding: '10px', color: '#a1a1aa' }}>{row.iops}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

      </div>
    </>
  );
}