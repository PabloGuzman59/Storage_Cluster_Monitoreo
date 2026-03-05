export default function NodeCard({ nodo, onClick }) {
  const isActive = nodo.status === 'active';
  
  let neonColor = '#333333'; 
  let neonGlow = 'transparent';

  if (isActive) {
    if (nodo.utilization > 90) {
      neonColor = '#ff003c'; 
      neonGlow = 'rgba(255, 0, 60, 0.4)';
    } else if (nodo.utilization > 70) {
      neonColor = '#ffea00'; 
      neonGlow = 'rgba(255, 234, 0, 0.4)';
    } else {
      neonColor = '#00ff66'; 
      neonGlow = 'rgba(0, 255, 102, 0.4)';
    }
  }

  return (
    <div 
      onClick={isActive ? onClick : null}
      style={{
        background: 'rgba(20, 20, 25, 0.6)', 
        backdropFilter: 'blur(12px)', 
        WebkitBackdropFilter: 'blur(12px)',
        borderRadius: '16px',
        padding: '24px',
        border: isActive ? `1px solid ${neonColor}` : '1px dashed #ef4444',
        boxShadow: isActive ? `0 0 15px ${neonGlow}, inset 0 0 10px rgba(255,255,255,0.02)` : 'none',
        cursor: isActive ? 'pointer' : 'not-allowed',
        transition: 'all 0.3s ease',
        opacity: isActive ? 1 : 0.5,
      }}
      onMouseEnter={(e) => isActive && (e.currentTarget.style.transform = 'translateY(-5px) scale(1.02)')}
      onMouseLeave={(e) => isActive && (e.currentTarget.style.transform = 'translateY(0) scale(1)')}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
        <h2 style={{ margin: 0, color: '#ffffff', fontSize: '20px', textShadow: isActive ? `0 0 5px ${neonColor}` : 'none' }}>
          {nodo.region}
        </h2>
        <span style={{ fontSize: '24px', filter: isActive ? `drop-shadow(0 0 5px ${neonColor})` : 'grayscale(100%)' }}>🖴</span>
      </div>

      {isActive ? (
        <>
          <p style={{ margin: '4px 0', color: '#a1a1aa', fontSize: '13px' }}>Capacidad: <strong style={{color: 'white'}}>{nodo.total_gb} GB</strong></p>
          <p style={{ margin: '4px 0', color: '#a1a1aa', fontSize: '13px' }}>En uso: <strong style={{color: 'white'}}>{nodo.used_gb} GB</strong></p>
          <p style={{ margin: '4px 0', color: '#a1a1aa', fontSize: '13px' }}>Libre: <strong style={{color: 'white'}}>{nodo.free_gb} GB</strong></p>
          
          <div style={{ marginTop: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '6px', fontWeight: 'bold', color: neonColor, textShadow: `0 0 5px ${neonGlow}` }}>
              <span>USO DEL DISCO</span>
              <span>{nodo.utilization}%</span>
            </div>
            <div style={{ width: '100%', height: '6px', backgroundColor: 'rgba(255,255,255,0.1)', borderRadius: '3px', overflow: 'hidden' }}>
              <div style={{ width: `${nodo.utilization}%`, height: '100%', backgroundColor: neonColor, boxShadow: `0 0 10px ${neonColor}`, transition: 'width 0.5s ease' }}></div>
            </div>
          </div>
        </>
      ) : (
        <div style={{ textAlign: 'center', padding: '20px 0' }}>
          <p style={{ color: '#ef4444', fontWeight: 'bold', margin: 0, textShadow: '0 0 5px rgba(239, 68, 68, 0.5)' }}>[ OFFLINE ]</p>
          <p style={{ color: '#52525b', fontSize: '12px', marginTop: '8px' }}>Señal perdida</p>
        </div>
      )}
    </div>
  );
}