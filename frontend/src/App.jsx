import { useCallback, useEffect, useRef, useState } from 'react'
import Chart from './Charts.jsx'

const ETAPES_MOTEUR = [
  'Lecture du fichier',
  'Détection des types de colonnes',
  'Analyse statistique',
  'Sélection des visualisations',
]

// ── Composants ──────────────────────────────────────────────────────────────
function Dropzone({ onFile, onSample }) {
  const [drag, setDrag] = useState(false)
  const inputRef = useRef(null)
  const handleDrop = useCallback((e) => {
    e.preventDefault(); setDrag(false)
    if (e.dataTransfer.files?.[0]) onFile(e.dataTransfer.files[0])
  }, [onFile])
  return (
    <div>
      <div className={'dropzone'+(drag?' drag':'')}
        onClick={()=>inputRef.current?.click()}
        onDragOver={(e)=>{e.preventDefault();setDrag(true)}}
        onDragLeave={()=>setDrag(false)}
        onDrop={handleDrop}
        role="button" tabIndex={0}
        onKeyDown={(e)=>e.key==='Enter'&&inputRef.current?.click()}>
        <div className="dropzone-icon">⬆</div>
        <div className="dropzone-title">Déposez votre fichier CSV ou Excel</div>
        <div className="dropzone-sub">ou cliquez pour parcourir · 10 Mo max · vos données ne sont pas conservées</div>
        <input ref={inputRef} type="file" accept=".csv,.xlsx,.xls" hidden
               onChange={(e)=>e.target.files?.[0]&&onFile(e.target.files[0])}/>
      </div>
      <div style={{textAlign:'center'}}>
        <button className="btn-sample" onClick={onSample}>
          Pas de fichier ? Essayer avec des données d'exemple →
        </button>
      </div>
    </div>
  )
}

function Moteur({ etape }) {
  return (
    <div className="engine">
      {ETAPES_MOTEUR.map((t,i)=>(
        <div key={t} className={'engine-line '+(i<etape?'done':i===etape?'active':'')}>
          <span className="engine-check">{i<etape?'✓':i===etape?'▸':'·'}</span>
          {t}{i===etape?'…':''}
        </div>
      ))}
    </div>
  )
}

// KPI avec couleur selon tendance
function KpiCard({ kpi }) {
  const positif = kpi.positif
  const estTendance = kpi.label === 'Tendance globale'
  const couleur = estTendance ? (positif ? '#0F766E' : '#DC2626') : undefined
  return (
    <div className="kpi">
      <div className="kpi-label">{kpi.label}</div>
      <div className="kpi-val" style={couleur ? {color:couleur} : undefined}>{kpi.valeur}</div>
    </div>
  )
}

function Resultats({ res, onReset }) {
  const p = res.profil
  const colonnes = Object.entries(p.colonnes)
  return (
    <div className="resultats container">
      <div className="fichier-bar">
        <div className="fichier-nom">{res.fichier}</div>
        <button className="btn-reset" onClick={onReset}>← Analyser un autre fichier</button>
      </div>

      {/* KPI métier */}
      {res.kpis && res.kpis.length > 0 && (
        <div className="kpi-grid">
          {res.kpis.map((k,i) => <KpiCard key={i} kpi={k}/>)}
        </div>
      )}

      {/* Métadonnées fichier (secondaire) */}
      <div style={{display:'flex',gap:12,flexWrap:'wrap',marginBottom:20,marginTop:8}}>
        {[
          ['Lignes',p.n_lignes.toLocaleString('fr-FR')],
          ['Colonnes',p.n_colonnes],
          ['Doublons',p.doublons],
          ['Graphiques',res.graphiques.length],
        ].map(([l,v])=>(
          <div key={l} style={{background:'#F0F4F8',borderRadius:8,padding:'6px 14px',fontSize:'0.82rem'}}>
            <span style={{color:'#6B6B76'}}>{l} : </span>
            <strong>{v}</strong>
          </div>
        ))}
      </div>

      {/* Insights */}
      <div className="insights">
        {res.insights.map((ins,i)=>(
          <div key={i} className={'insight '+ins.niveau}>
            <span>{ins.niveau==='alerte'?'▲':ins.niveau==='info'?'◆':'✓'}</span>
            <span>{ins.texte}</span>
          </div>
        ))}
      </div>

      {/* Graphiques */}
      <div className="charts-grid">
        {res.graphiques.map((g,i)=>(
          <div key={i} className="chart-card">
            <div className="chart-titre">{g.titre}</div>
            <div className="chart-raison">{g.raison}</div>
            <Chart graphe={g}/>
          </div>
        ))}
      </div>

      {/* Aperçu données */}
      <div className="apercu">
        <h3>Aperçu des données · types détectés automatiquement</h3>
        <div className="apercu-scroll">
          <table>
            <thead>
              <tr>{colonnes.map(([nom,info])=>(
                <th key={nom}>{nom}<span className="type-badge">{info.type}</span></th>
              ))}</tr>
            </thead>
            <tbody>
              {res.apercu.map((ligne,i)=>(
                <tr key={i}>{colonnes.map(([nom])=><td key={nom}>{String(ligne[nom]??'')}</td>)}</tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

// Preview statique pour le hero
function HeroPreview() {
  return (
    <div style={{maxWidth:820,margin:'48px auto 0',background:'#fff',border:'1px solid #E7E5E0',borderRadius:16,overflow:'hidden',boxShadow:'0 4px 24px rgba(0,0,0,.06)'}}>
      <div style={{background:'#F8FAFC',borderBottom:'1px solid #E7E5E0',padding:'12px 20px',display:'flex',alignItems:'center',gap:8}}>
        <div style={{width:10,height:10,borderRadius:'50%',background:'#DC2626'}}/>
        <div style={{width:10,height:10,borderRadius:'50%',background:'#D97706'}}/>
        <div style={{width:10,height:10,borderRadius:'50%',background:'#16A34A'}}/>
        <span style={{marginLeft:8,fontSize:'0.78rem',color:'#6B6B76',fontFamily:'JetBrains Mono, monospace'}}>DashGen · exemple_ventes.csv</span>
      </div>
      <div style={{padding:'16px 20px'}}>
        <div style={{display:'grid',gridTemplateColumns:'repeat(4,1fr)',gap:10,marginBottom:16}}>
          {[['CA Total','49.2 M'],['Moy. / semaine','950 K'],['Période','Jan–Déc 2025'],['Tendance','▼ 11%']].map(([l,v])=>(
            <div key={l} style={{background:'#F8FAFC',borderRadius:8,padding:'10px 12px',border:'1px solid #E7E5E0'}}>
              <div style={{fontSize:'0.65rem',color:'#6B6B76',textTransform:'uppercase',letterSpacing:'0.06em'}}>{l}</div>
              <div style={{fontFamily:'Space Grotesk, sans-serif',fontWeight:700,fontSize:'1.1rem',marginTop:3,color:l==='Tendance'?'#DC2626':'#15151A'}}>{v}</div>
            </div>
          ))}
        </div>
        <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:10}}>
          {[
            {t:'Montant TTC dans le temps',tag:'ligne'},
            {t:'Montant TTC par Dépôt',tag:'barres'},
          ].map(d=>(
            <div key={d.t} style={{background:'#fff',border:'1px solid #E7E5E0',borderRadius:10,padding:'12px 14px'}}>
              <div style={{fontWeight:600,fontSize:'0.85rem',marginBottom:4}}>{d.t}</div>
              <div style={{fontFamily:'JetBrains Mono, monospace',fontSize:'0.65rem',color:'#3730A3',background:'#EEF2FF',borderRadius:5,padding:'4px 8px',marginBottom:10}}>
                ⟨ moteur ⟩ Graphique {d.tag} recommandé automatiquement
              </div>
              <div style={{height:70,background:'#F8FAFC',borderRadius:6,display:'flex',alignItems:'flex-end',padding:'8px 8px 0',gap:4}}>
                {d.tag==='ligne'
                  ? [40,55,48,72,65,58,80,71,63,85,77,60].map((h,i)=>(
                      <div key={i} style={{flex:1,height:`${h}%`,background:'#4F46E5',opacity:0.15+i*0.07,borderRadius:'2px 2px 0 0'}}/>
                    ))
                  : ['Casa','Rabat','Marra'].map((l,i)=>(
                      <div key={l} style={{flex:1,display:'flex',flexDirection:'column',alignItems:'center',gap:4}}>
                        <div style={{width:'100%',height:[65,42,38][i]+'%',background:['#4F46E5','#0F766E','#B45309'][i],borderRadius:'3px 3px 0 0',opacity:0.85}}/>
                        <div style={{fontSize:9,color:'#6B6B76'}}>{l}</div>
                      </div>
                    ))
                }
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ── App principale ──────────────────────────────────────────────────────────
export default function App() {
  const [etat, setEtat] = useState('accueil')
  const [etape, setEtape] = useState(0)
  const [res, setRes] = useState(null)
  const [erreur, setErreur] = useState(null)

  useEffect(() => {
    if (etat !== 'analyse') return
    const timer = setInterval(()=>setEtape(e=>Math.min(e+1,ETAPES_MOTEUR.length-1)), 650)
    return () => clearInterval(timer)
  }, [etat])

  const analyser = async (file) => {
    setErreur(null); setEtape(0); setEtat('analyse')
    const form = new FormData()
    form.append('file', file)
    try {
      const r = await fetch('/api/analyze', {method:'POST', body:form})
      if (!r.ok) {
        const detail = (await r.json().catch(()=>null))?.detail
        throw new Error(detail || `Erreur ${r.status}`)
      }
      const data = await r.json()
      setEtape(ETAPES_MOTEUR.length)
      setTimeout(()=>{ setRes(data); setEtat('resultats') }, 400)
    } catch(e) {
      setErreur(e.message); setEtat('accueil')
    }
  }

  const chargerExemple = async () => {
    const r = await fetch('/exemple_ventes.csv')
    const blob = await r.blob()
    analyser(new File([blob], 'exemple_ventes.csv', {type:'text/csv'}))
  }

  return (
    <>
      <header>
        <div className="container">
          <div className="logo">Dash<span>Gen</span></div>
          <div className="header-credit">
            par <a href="https://github.com/Davlamelo" target="_blank" rel="noreferrer">T. Ulrich David</a>
          </div>
        </div>
      </header>

      {etat === 'accueil' && (
        <div className="hero container">
          <h1>Vos données. <em>Votre dashboard.</em><br/>En 30 secondes.</h1>
          <p>Déposez un fichier CSV ou Excel : le moteur détecte la structure de vos données et génère automatiquement les visualisations les plus pertinentes — en expliquant ses choix.</p>
          <Dropzone onFile={analyser} onSample={chargerExemple}/>
          {erreur && <div className="erreur">{erreur}</div>}
          <HeroPreview/>
          <div className="etapes">
            <div className="etape"><div className="etape-num">01</div><div className="etape-titre">Déposez</div><div className="etape-desc">CSV ou Excel, brut ou propre. Séparateurs et formats détectés automatiquement.</div></div>
            <div className="etape"><div className="etape-num">02</div><div className="etape-titre">Le moteur analyse</div><div className="etape-desc">Types, distributions, corrélations, qualité des données.</div></div>
            <div className="etape"><div className="etape-num">03</div><div className="etape-titre">Explorez</div><div className="etape-desc">Graphiques pertinents, KPI métier, insights — et le raisonnement derrière chaque choix.</div></div>
          </div>
        </div>
      )}

      {etat === 'analyse' && <Moteur etape={etape}/>}
      {etat === 'resultats' && res && <Resultats res={res} onReset={()=>{setRes(null);setEtat('accueil')}}/>}

      <footer>
        DashGen — génération automatique de dashboards ·{' '}
        <a href="https://github.com/Davlamelo" target="_blank" rel="noreferrer">github.com/Davlamelo</a>
      </footer>
    </>
  )
}
