import {
  Bar, BarChart, CartesianGrid, Cell, Label, Line, LineChart, Pie, PieChart,
  ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis,
} from 'recharts'

const INDIGO = '#4F46E5'
const PALETTE = ['#4F46E5','#0F766E','#B45309','#7C3AED','#0E7490','#BE185D','#4D7C0F','#6B7280']

const fmt = (v) => {
  if (typeof v !== 'number') return v
  if (Math.abs(v) >= 1_000_000) return (v/1_000_000).toFixed(1)+' M'
  if (Math.abs(v) >= 10_000)    return (v/1_000).toFixed(0)+' K'
  return Number.isInteger(v) ? v.toLocaleString('fr-FR') : v.toFixed(2)
}

// Tooltip blanc, texte sombre — lisible partout
const tip = {
  background:'#FFFFFF',
  border:'1px solid #E7E5E0',
  borderRadius:8,
  color:'#15151A',
  fontSize:12,
  fontFamily:'Inter, sans-serif',
  boxShadow:'0 4px 12px rgba(0,0,0,.10)',
}

const LabelDonut = ({ cx, cy, midAngle, outerRadius, percent, name }) => {
  if (percent < 0.06) return null
  const RADIAN = Math.PI / 180
  const r = outerRadius + 24
  const x = cx + r * Math.cos(-midAngle * RADIAN)
  const y = cy + r * Math.sin(-midAngle * RADIAN)
  return (
    <text x={x} y={y} fill="#15151A" textAnchor={x > cx ? 'start' : 'end'}
          dominantBaseline="central" fontSize={11}>
      {name} {(percent*100).toFixed(0)}%
    </text>
  )
}

export default function Chart({ graphe }) {
  const { type, data, x, y } = graphe
  const hx = x, hy = y   // labels humains déjà formatés par le backend

  if (type === 'ligne') return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={data} margin={{top:4,right:8,left:0,bottom:32}}>
        <CartesianGrid stroke="#F0EFEA" vertical={false}/>
        <XAxis dataKey="x" tick={{fontSize:10,fill:'#6B6B76'}} tickLine={false}
               axisLine={{stroke:'#E7E5E0'}} minTickGap={32}>
          <Label value={hx} position="insideBottom" offset={-20} fontSize={11} fill="#6B6B76"/>
        </XAxis>
        <YAxis tick={{fontSize:11,fill:'#6B6B76'}} tickLine={false} axisLine={false}
               tickFormatter={fmt} width={56}>
          <Label value={hy} angle={-90} position="insideLeft" offset={14} fontSize={11} fill="#6B6B76"/>
        </YAxis>
        <Tooltip contentStyle={tip} formatter={(v)=>[fmt(v), hy]} labelFormatter={(l)=>l}/>
        <Line type="monotone" dataKey="y" stroke={INDIGO} strokeWidth={2.2}
              dot={false} activeDot={{r:4}}/>
      </LineChart>
    </ResponsiveContainer>
  )

  if (type === 'barres' || type === 'histogramme') return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} margin={{top:4,right:8,left:0,bottom:42}}>
        <CartesianGrid stroke="#F0EFEA" vertical={false}/>
        <XAxis dataKey="x" tick={{fontSize:10,fill:'#6B6B76'}} tickLine={false}
               axisLine={{stroke:'#E7E5E0'}} angle={-25} textAnchor="end" height={52}>
          <Label value={hx} position="insideBottom" offset={-30} fontSize={11} fill="#6B6B76"/>
        </XAxis>
        <YAxis tick={{fontSize:11,fill:'#6B6B76'}} tickLine={false} axisLine={false}
               tickFormatter={fmt} width={56}>
          <Label value={hy} angle={-90} position="insideLeft" offset={14} fontSize={11} fill="#6B6B76"/>
        </YAxis>
        <Tooltip contentStyle={tip} formatter={(v)=>[fmt(v), hy]} cursor={{fill:'#EEF2FF'}}/>
        <Bar dataKey="y" fill={INDIGO} radius={[4,4,0,0]} maxBarSize={42}/>
      </BarChart>
    </ResponsiveContainer>
  )

  if (type === 'scatter') return (
    <ResponsiveContainer width="100%" height={260}>
      <ScatterChart margin={{top:4,right:8,left:0,bottom:32}}>
        <CartesianGrid stroke="#F0EFEA"/>
        <XAxis dataKey="x" name={hx} type="number" tick={{fontSize:11,fill:'#6B6B76'}}
               tickLine={false} axisLine={{stroke:'#E7E5E0'}} tickFormatter={fmt}
               domain={['auto','auto']}>
          <Label value={hx} position="insideBottom" offset={-20} fontSize={11} fill="#6B6B76"/>
        </XAxis>
        <YAxis dataKey="y" name={hy} type="number" tick={{fontSize:11,fill:'#6B6B76'}}
               tickLine={false} axisLine={false} tickFormatter={fmt} width={56}
               domain={['auto','auto']}>
          <Label value={hy} angle={-90} position="insideLeft" offset={14} fontSize={11} fill="#6B6B76"/>
        </YAxis>
        <Tooltip contentStyle={tip} formatter={(v,n)=>[fmt(v),n]} cursor={{strokeDasharray:'4 4'}}/>
        <Scatter data={data} fill={INDIGO} fillOpacity={0.55}/>
      </ScatterChart>
    </ResponsiveContainer>
  )

  if (type === 'donut') {
    const dataClean = data.map(d => ({...d, y: Math.round(Number(d.y))}))
    return (
      <ResponsiveContainer width="100%" height={280}>
        <PieChart>
          <Pie data={dataClean} dataKey="y" nameKey="x"
               innerRadius={60} outerRadius={95} paddingAngle={2} strokeWidth={0}
               labelLine={true} label={LabelDonut}>
            {dataClean.map((_,i) => <Cell key={i} fill={PALETTE[i%PALETTE.length]}/>)}
          </Pie>
          <Tooltip contentStyle={tip} formatter={(v,n)=>[v.toLocaleString('fr-FR'), n]}/>
        </PieChart>
      </ResponsiveContainer>
    )
  }

  return null
}
