import { useState, useEffect } from 'react';
import NodeCard from './NodeCard';
import NodeHistory from './NodeHistory';

const DEPARTAMENTOS_BOLIVIA = [
  "La Paz", "Cochabamba", "Santa Cruz", "Oruro", 
  "Potosí", "Chuquisaca", "Tarija", "Beni", "Pando"
];

export default function Dashboard() {
  const [nodosBD, setNodosBD] = useState([]);
  const [resumen, setResumen] = useState({});
  const [nodoSeleccionado, setNodoSeleccionado] = useState(null);

  const fetchData = () => {
    fetch('/api/nodes').then(res => res.json()).then(data => setNodosBD(data));
    fetch('/api/summary').then(res => res.json()).then(data => setResumen(data));
  };

useEffect(() => {
    fetchData(); 
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, []);
  const nodosCompletos = DEPARTAMENTOS_BOLIVIA.map(dep => {
    const infoBD = nodosBD.find(n => n.region.toLowerCase() === dep.toLowerCase());
    return infoBD ? infoBD : { client_id: `offline_${dep}`, region: dep, status: 'no_reporta' };
  });

  const pct = resumen.utilization_pct || 0;
  const globalColor = pct > 80 ? '#ff003c' : pct > 60 ? '#ffea00' : '#00f3ff';

  return (
    <div style={{ padding: '40px', width: '100%', minHeight: '100vh' }}>
      
      <div style={{ 
        display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '40px', 
        background: 'rgba(20, 20, 25, 0.5)', backdropFilter: 'blur(10px)', WebkitBackdropFilter: 'blur(10px)',
        padding: '30px', borderRadius: '20px', border: '1px solid rgba(255,255,255,0.05)', 
        boxShadow: '0 10px 30px rgba(0,0,0,0.5)' 
      }}>
        <div>
          <h1 style={{ margin: '0 0 5px 0', fontSize: '32px', color: '#ffffff', textShadow: '0 0 10px rgba(255,255,255,0.3)' }}>CNS CORE MONITOR</h1>
          <p style={{ color: '#00f3ff', margin: 0, fontSize: '16px', letterSpacing: '2px', textShadow: '0 0 5px rgba(0, 243, 255, 0.5)' }}>STORAGE CLUSTER LINK</p>
        </div>
        
        <div style={{ display: 'flex', gap: '40px', textAlign: 'right', alignItems: 'center' }}>
          <div>
            <p style={{ margin: '0 0 5px 0', color: '#a1a1aa', fontSize: '12px', letterSpacing: '1px' }}>TOTAL CLUSTER</p>
            <p style={{ margin: 0, fontSize: '24px', fontWeight: 'bold', color: 'white' }}>{resumen.cluster_total_gb || 0} <span style={{fontSize:'14px', color:'#a1a1aa'}}>GB</span></p>
          </div>
          <div>
            <p style={{ margin: '0 0 5px 0', color: '#a1a1aa', fontSize: '12px', letterSpacing: '1px' }}>NODOS ACTIVOS</p>
            <p style={{ margin: 0, fontSize: '24px', fontWeight: 'bold', color: '#00ff66', textShadow: '0 0 10px rgba(0,255,102,0.4)' }}>{resumen.active_nodes || 0} <span style={{fontSize:'14px', color:'#a1a1aa'}}>/ 9</span></p>
          </div>
          
          <div style={{ 
            borderLeft: '1px solid rgba(255,255,255,0.1)', paddingLeft: '40px',
            display: 'flex', flexDirection: 'column', alignItems: 'center'
          }}>
             <p style={{ margin: '0 0 5px 0', color: '#a1a1aa', fontSize: '12px', letterSpacing: '1px' }}>LLENADO GLOBAL</p>
             <h2 style={{ margin: 0, fontSize: '42px', color: globalColor, textShadow: `0 0 20px ${globalColor}80` }}>
               {pct}%
             </h2>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '24px' }}>
        {nodosCompletos.map((nodo) => (
          <NodeCard key={nodo.client_id} nodo={nodo} onClick={() => setNodoSeleccionado(nodo)} />
        ))}
      </div>

      {nodoSeleccionado && (
        <>
          <div onClick={() => setNodoSeleccionado(null)} style={{ position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', backgroundColor: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(3px)', zIndex: 999 }}></div>
          <NodeHistory client_id={nodoSeleccionado.client_id} region={nodoSeleccionado.region} onClose={() => setNodoSeleccionado(null)} />
        </>
      )}
    </div>
  );
}