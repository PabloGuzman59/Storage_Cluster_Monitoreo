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
  const [logs, setLogs] = useState([]);
  
  // Estados para el envío de comandos
  const [targetNode, setTargetNode] = useState('__broadcast__');
  const [commandText, setCommandText] = useState('');
  const [commandStatus, setCommandStatus] = useState('');

  const fetchData = () => {
    fetch('/api/nodes').then(res => res.json()).then(data => setNodosBD(data));
    fetch('/api/summary').then(res => res.json()).then(data => setResumen(data));
    
    fetch('/api/logs')
      .then(res => res.json())
      .then(data => setLogs(data))
      .catch(() => {
        setLogs([
          "[SYSTEM] Inicializando módulo de consola de eventos...",
          "[INFO] Esperando a que el equipo de Backend habilite la ruta '/api/logs'..."
        ]);
      });
  };

  useEffect(() => {
    fetchData(); 
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, []);

  // Función para enviar el mensaje al Python
  const handleSendCommand = async (e) => {
    e.preventDefault();
    if (!commandText.trim()) return;

    setCommandStatus('Enviando...');

    // Flask espera form-data, no JSON plano
    const formData = new URLSearchParams();
    formData.append('client_id', targetNode);
    formData.append('message', commandText);

    try {
      const response = await fetch('/send_message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData.toString()
      });

      if (response.ok) {
        setCommandStatus('¡Comando enviado con éxito!');
        setCommandText(''); // Limpiamos la cajita
      } else {
        setCommandStatus('❌ Error al enviar el comando.');
      }
    } catch (err) {
      setCommandStatus('❌ Error de conexión con el servidor.');
    }

    // Borramos el mensajito de éxito/error después de 3 segundos
    setTimeout(() => setCommandStatus(''), 3000);
  };

  const nodosCompletos = DEPARTAMENTOS_BOLIVIA.map(dep => {
    const infoBD = nodosBD.find(n => n.region.toLowerCase() === dep.toLowerCase());
    return infoBD ? infoBD : { client_id: `offline_${dep}`, region: dep, status: 'no_reporta' };
  });

  const pct = resumen.utilization_pct || 0;
  const globalColor = pct > 80 ? '#ff003c' : pct > 60 ? '#ffea00' : '#00f3ff';

  return (
    <>
      <style>
        {`
          .no-scrollbar::-webkit-scrollbar { width: 6px; }
          .no-scrollbar::-webkit-scrollbar-track { background: transparent; }
          .no-scrollbar::-webkit-scrollbar-thumb { background: rgba(0, 243, 255, 0.3); border-radius: 10px; }
          .no-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(0, 243, 255, 0.6); }
          .neon-input:focus { border-color: #00ff66 !important; box-shadow: 0 0 15px rgba(0,255,102,0.4) !important; }
          .btn-neon:hover { background: #00cc55 !important; transform: scale(1.02); }
        `}
      </style>

      <div style={{ padding: '40px', width: '100%', minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
        
        {/* HEADER */}
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

        {/* GRID DE TARJETAS */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '24px', flexGrow: 1 }}>
          {nodosCompletos.map((nodo) => (
            <NodeCard key={nodo.client_id} nodo={nodo} onClick={() => setNodoSeleccionado(nodo)} />
          ))}
        </div>

        {/* ESTACIÓN DE CONTROL (COMANDOS + LOGS) */}
        <div style={{ marginTop: '40px', display: 'flex', gap: '24px' }}>
          
          {/* PANEL DE ENVÍO DE COMANDOS */}
          <div style={{ 
            flex: '1', background: 'rgba(20, 25, 20, 0.85)', 
            border: '1px solid rgba(0, 255, 102, 0.3)', borderRadius: '15px', 
            padding: '25px', boxShadow: '0 10px 30px rgba(0,0,0,0.5)' 
          }}>
            <h3 style={{ color: '#00ff66', margin: '0 0 20px 0', fontSize: '14px', letterSpacing: '2px', display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span style={{ display: 'inline-block', width: '8px', height: '8px', background: '#00ff66', borderRadius: '50%', boxShadow: '0 0 10px #00ff66' }}></span>
              PANEL DE COMANDOS (BIDIRECCIONAL)
            </h3>
            
            <form onSubmit={handleSendCommand} style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
              <div style={{ display: 'flex', gap: '15px' }}>
                <select 
                  value={targetNode} 
                  onChange={(e) => setTargetNode(e.target.value)}
                  style={{ width: '30%', background: 'rgba(0,0,0,0.6)', color: 'white', border: '1px solid rgba(255,255,255,0.1)', padding: '12px', borderRadius: '8px', outline: 'none', cursor: 'pointer' }}
                >
                  <option value="__broadcast__">📡 TODOS (BROADCAST)</option>
                  {nodosBD.filter(n => n.status === 'active').map(n => (
                    <option key={n.client_id} value={n.client_id}>▶ {n.region.toUpperCase()}</option>
                  ))}
                </select>

                <input 
                  type="text" 
                  value={commandText}
                  onChange={(e) => setCommandText(e.target.value)}
                  className="neon-input"
                  placeholder="Ej: Reinicie servicio, Verifique espacio en disco..."
                  style={{ flexGrow: 1, background: 'rgba(0,0,0,0.6)', color: '#00f3ff', border: '1px solid rgba(0, 243, 255, 0.3)', padding: '12px 15px', borderRadius: '8px', outline: 'none', transition: 'all 0.3s' }}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ color: '#00ff66', fontSize: '13px', fontStyle: 'italic', opacity: commandStatus ? 1 : 0, transition: 'opacity 0.3s' }}>
                  {commandStatus}
                </span>
                <button 
                  type="submit" 
                  className="btn-neon"
                  style={{ background: '#00ff66', color: '#000', fontWeight: 'bold', letterSpacing: '1px', border: 'none', padding: '12px 30px', borderRadius: '8px', cursor: 'pointer', transition: 'all 0.2s', boxShadow: '0 0 15px rgba(0,255,102,0.3)' }}
                >
                  EJECUTAR COMANDO
                </button>
              </div>
            </form>
          </div>



        </div>

        {/* MODAL HISTORIAL */}
        {nodoSeleccionado && (
          <>
            <div onClick={() => setNodoSeleccionado(null)} style={{ position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', backgroundColor: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(3px)', zIndex: 999 }}></div>
            <NodeHistory client_id={nodoSeleccionado.client_id} region={nodoSeleccionado.region} onClose={() => setNodoSeleccionado(null)} />
          </>
        )}
      </div>
    </>
  );
}