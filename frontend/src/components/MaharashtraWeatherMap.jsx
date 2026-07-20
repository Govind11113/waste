import { useEffect, useState, useMemo } from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import { MapContainer, TileLayer, GeoJSON, CircleMarker, Popup, Tooltip, ZoomControl } from 'react-leaflet'
import mhGeoJson from '../data/maharashtra.geojson?url'
import { scaleReveal } from '../utils/motion'

/**
 * @typedef {{
 *   temperature_2m: number,
 *   relative_humidity_2m: number,
 *   weather_code: number,
 *   wind_speed_10m?: number,
 *   apparent_temperature?: number,
 * }} WeatherReading
 * @typedef {'street' | 'terrain' | 'light'} TileStyle
 */

const CITIES = [
  { name: 'Mumbai',     lat: 19.0760, lon: 72.8777, type: 'Metro' },
  { name: 'Pune',       lat: 18.5204, lon: 73.8567, type: 'IT Hub' },
  { name: 'Nashik',     lat: 19.9975, lon: 73.7898, type: 'Industrial' },
  { name: 'Nagpur',     lat: 21.1458, lon: 79.0882, type: 'Vidarbha' },
  { name: 'Aurangabad', lat: 19.8762, lon: 75.3433, type: 'Marathwada' },
  { name: 'Kolhapur',   lat: 16.7050, lon: 74.2433, type: 'South' },
  { name: 'Amravati',   lat: 20.9374, lon: 77.7796, type: 'Vidarbha' },
  { name: 'Solapur',    lat: 17.6599, lon: 75.9064, type: 'East' },
  { name: 'Thane',      lat: 19.2183, lon: 72.9781, type: 'Konkan' },
]

/** @type {Record<number, string>} */
const WEATHER_DESCRIPTIONS = {
  0: 'Clear', 1: 'Mostly Clear', 2: 'Partly Cloudy', 3: 'Overcast',
  45: 'Foggy', 48: 'Foggy', 51: 'Light Drizzle', 53: 'Drizzle', 55: 'Heavy Drizzle',
  61: 'Light Rain', 63: 'Rain', 65: 'Heavy Rain', 71: 'Light Snow',
  73: 'Snow', 75: 'Heavy Snow', 80: 'Showers', 81: 'Showers', 82: 'Heavy Showers',
  95: 'Thunderstorm', 96: 'Thunderstorm', 99: 'Severe Thunderstorm',
}

/** @type {Record<number, string>} */
const WEATHER_ICONS = {
  0: 'wb_sunny', 1: 'wb_sunny', 2: 'partly_cloudy_day', 3: 'cloud',
  45: 'foggy', 48: 'foggy', 51: 'rainy', 53: 'rainy', 55: 'rainy',
  61: 'rainy', 63: 'rainy', 65: 'thunderstorm', 71: 'weather_snowy',
  73: 'weather_snowy', 75: 'weather_snowy', 80: 'rainy', 81: 'rainy', 82: 'thunderstorm',
  95: 'thunderstorm', 96: 'thunderstorm', 99: 'thunderstorm',
}

/** @param {number | null | undefined} t */
function tempColor(t) {
  if (t == null) return '#9ca3af'
  if (t >= 38) return '#dc2626'
  if (t >= 32) return '#f97316'
  if (t >= 26) return '#eab308'
  if (t >= 20) return '#16a34a'
  return '#0284c7'
}

/** @param {number | null | undefined} t */
function tempBand(t) {
  if (t == null) return 'Loading'
  if (t >= 38) return 'Extreme Heat'
  if (t >= 32) return 'Hot'
  if (t >= 26) return 'Warm'
  if (t >= 20) return 'Mild'
  return 'Cool'
}

function MaharashtraWeatherMap({ compact = false }) {
  const [weather, setWeather] = useState(/** @type {Record<string, WeatherReading>} */ ({}))
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(/** @type {string | null} */ (null))
  const [warning, setWarning] = useState(/** @type {string | null} */ (null))
  const [geoData, setGeoData] = useState(/** @type {import('geojson').FeatureCollection | null} */ (null))
  const [tileStyle, setTileStyle] = useState(/** @type {TileStyle} */ ('street'))

  useEffect(() => {
    const controller = new AbortController()
    fetch(mhGeoJson, { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error('Boundary data unavailable')
        return response.json()
      })
      .then(setGeoData)
      .catch((caught) => {
        if (!(caught instanceof DOMException && caught.name === 'AbortError')) {
          setWarning('The Maharashtra boundary overlay could not be loaded.')
        }
      })
    return () => controller.abort()
  }, [])

  useEffect(() => {
    const controller = new AbortController()

    const fetchAll = async () => {
      const settled = await Promise.allSettled(CITIES.map(async (city) => {
        const url = `https://api.open-meteo.com/v1/forecast?latitude=${city.lat}&longitude=${city.lon}&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m,apparent_temperature&timezone=Asia%2FKolkata`
        const response = await fetch(url, { signal: controller.signal })
        if (!response.ok) throw new Error(`Weather unavailable for ${city.name}`)
        const data = await response.json()
        return [city.name, data.current]
      }))

      if (controller.signal.aborted) return
      const successful = settled
        .filter((item) => item.status === 'fulfilled')
        .map((item) => item.value)
      const failedCount = settled.length - successful.length

      if (successful.length === 0) {
        setError(null)
        setWarning('Live weather is unavailable. The Maharashtra map and city locations remain available.')
        setWeather({})
      } else {
        setWeather(Object.fromEntries(successful))
        if (failedCount > 0) {
          setWarning(`Live weather is available for ${successful.length} of ${CITIES.length} cities.`)
        }
      }
      setLoading(false)
    }

    fetchAll().catch((caught) => {
      if (controller.signal.aborted) return
      const detail = caught instanceof Error ? caught.message : 'Live weather temporarily unavailable'
      setError(null)
      setWarning(`${detail}. The map remains available without live readings.`)
      setWeather({})
      setLoading(false)
    })
    return () => controller.abort()
  }, [])

  const avgTemp = useMemo(() => {
    const temps = Object.values(weather).map(w => w?.temperature_2m).filter(t => t != null)
    if (!temps.length) return null
    return temps.reduce((a, b) => a + b, 0) / temps.length
  }, [weather])

  const avgHumidity = useMemo(() => {
    const hs = Object.values(weather).map(w => w?.relative_humidity_2m).filter(h => h != null)
    if (!hs.length) return null
    return hs.reduce((a, b) => a + b, 0) / hs.length
  }, [weather])

  const hottest = useMemo(() => {
    const list = Object.entries(weather).filter(([, w]) => w?.temperature_2m != null)
    if (!list.length) return null
    return list.reduce((a, b) => a[1].temperature_2m > b[1].temperature_2m ? a : b)
  }, [weather])

  const coolest = useMemo(() => {
    const list = Object.entries(weather).filter(([, w]) => w?.temperature_2m != null)
    if (!list.length) return null
    return list.reduce((a, b) => a[1].temperature_2m < b[1].temperature_2m ? a : b)
  }, [weather])

  const advisory = useMemo(() => {
    if (avgTemp == null || avgHumidity == null) return null
    const hot = avgTemp >= 32
    const humid = avgHumidity >= 70
    if (hot && humid) return { tone: 'error', icon: 'warning', msg: 'High temperature and humidity detected. IT lab equipment under thermal stress. Increase AC cooling, ensure ventilation, and avoid heavy compute workloads during peak afternoon hours.' }
    if (hot) return { tone: 'warning', icon: 'thermostat', msg: 'Elevated ambient temperature across the state. Schedule heavy server workloads for cooler night hours and verify lab AC units are operational.' }
    if (humid) return { tone: 'warning', icon: 'water_drop', msg: 'High humidity levels. Keep electronics in well-ventilated, dust-controlled spaces. Check for condensation on lab equipment and use silica gel in storage cabinets.' }
    return { tone: 'success', icon: 'check_circle', msg: 'Conditions favorable for electronics across the state. Standard maintenance schedule recommended.' }
  }, [avgTemp, avgHumidity])

  const geoStyle = {
    fillColor: 'var(--primary)',
    weight: 2.5,
    opacity: 1,
    color: 'var(--primary)',
    fillOpacity: 0.12,
    dashArray: '0',
  }

  /** @type {Record<TileStyle, { url: string, attribution: string }>} */
  const tileConfigs = {
    street: {
      url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
    },
    terrain: {
      url: 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
      attribution: 'Map data: &copy; OpenStreetMap, SRTM | Map style: &copy; OpenTopoMap'
    },
    light: {
      url: 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
      attribution: '&copy; OpenStreetMap, &copy; CARTO'
    },
  }
  const activeTile = tileConfigs[tileStyle]

  const reduce = useReducedMotion()
  const containerVariants = reduce
    ? { hidden: { opacity: 1 }, visible: { opacity: 1 } }
    : scaleReveal

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="bg-surface-container-lowest rounded-xl p-6 hover-lift card-shadow"
    >
      <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
        <div>
          <h3 className="text-xl font-bold text-on-surface flex items-center gap-2">
            <span className="material-symbols-outlined text-primary">map</span>
            Maharashtra Live Weather Map
          </h3>
          <p className="text-sm text-on-surface-variant mt-1">Real-time conditions across {CITIES.length} cities — Open-Meteo + OpenStreetMap</p>
        </div>
        {avgTemp != null && avgHumidity != null && (
          <div className="flex gap-2 flex-wrap">
            <div className="bg-surface-container rounded-lg px-3 py-2 text-center min-w-[80px]">
              <p className="text-[10px] text-on-surface-variant uppercase tracking-wider">Avg Temp</p>
              <p className="text-lg font-black" style={{color: tempColor(avgTemp)}}>{avgTemp.toFixed(1)}°C</p>
            </div>
            <div className="bg-surface-container rounded-lg px-3 py-2 text-center min-w-[80px]">
              <p className="text-[10px] text-on-surface-variant uppercase tracking-wider">Humidity</p>
              <p className="text-lg font-black text-secondary">{avgHumidity.toFixed(0)}%</p>
            </div>
            {hottest && (
              <div className="bg-surface-container rounded-lg px-3 py-2 text-center min-w-[100px]">
                <p className="text-[10px] text-on-surface-variant uppercase tracking-wider">Hottest</p>
                <p className="text-sm font-black text-on-surface">{hottest[0]}</p>
                <p className="text-xs font-bold" style={{color: tempColor(hottest[1].temperature_2m)}}>{hottest[1].temperature_2m.toFixed(1)}°C</p>
              </div>
            )}
            {coolest && (
              <div className="bg-surface-container rounded-lg px-3 py-2 text-center min-w-[100px]">
                <p className="text-[10px] text-on-surface-variant uppercase tracking-wider">Coolest</p>
                <p className="text-sm font-black text-on-surface">{coolest[0]}</p>
                <p className="text-xs font-bold" style={{color: tempColor(coolest[1].temperature_2m)}}>{coolest[1].temperature_2m.toFixed(1)}°C</p>
              </div>
            )}
          </div>
        )}
      </div>

      {error ? (
        <div className="p-4 bg-error-container/40 rounded-xl text-sm text-on-surface-variant flex items-center gap-2">
          <span className="material-symbols-outlined text-error">cloud_off</span>
          {error}
        </div>
      ) : (
        <>
          {warning && (
            <div role="status" className="mb-4 p-3 bg-tertiary/10 border border-tertiary/30 rounded-xl text-sm text-on-surface flex items-center gap-2">
              <span className="material-symbols-outlined text-tertiary" aria-hidden="true">info</span>
              {warning}
            </div>
          )}
          <div className="flex gap-2 mb-3 flex-wrap" role="group" aria-label="Map background style">
            {(/** @type {TileStyle[]} */ (Object.keys(tileConfigs))).map(k => (
              <button
                key={k}
                type="button"
                aria-pressed={tileStyle === k}
                onClick={() => setTileStyle(k)}
                className={`px-3 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider transition-all ${
                  tileStyle === k ? 'bg-primary text-on-primary shadow-md' : 'bg-surface-container text-on-surface-variant hover:bg-surface-container-high'
                }`}
              >
                {k === 'street' ? 'Street' : k === 'terrain' ? 'Terrain' : 'Light'}
              </button>
            ))}
          </div>

          <div className="relative rounded-xl overflow-hidden border border-outline-variant" style={{height: compact ? '420px' : '520px'}}>
            <MapContainer
              center={[19.5, 76.0]}
              zoom={6}
              minZoom={5}
              maxZoom={11}
              scrollWheelZoom={false}
              zoomControl={false}
              className="w-full h-full"
              style={{background: 'var(--surface-container)'}}
            >
              <TileLayer key={tileStyle} url={activeTile.url} attribution={activeTile.attribution} />
              <ZoomControl position="topright" />

              {geoData && <GeoJSON data={geoData} style={geoStyle} />}

              {CITIES.map((city) => {
                const w = weather[city.name]
                const t = w?.temperature_2m
                const color = tempColor(t)
                const radius = t != null ? 14 : 8
                return (
                  <CircleMarker
                    key={city.name}
                    center={[city.lat, city.lon]}
                    radius={radius}
                    pathOptions={{
                      fillColor: color,
                      color: '#ffffff',
                      weight: 3,
                      fillOpacity: 0.9,
                    }}
                  >
                    <Tooltip direction="top" offset={[0, -12]} opacity={1} permanent={!loading && t != null}>
                      <div style={{textAlign: 'center', fontFamily: 'Inter, sans-serif'}}>
                        <div style={{fontWeight: 700, fontSize: 12}}>{city.name}</div>
                        {t != null && <div style={{fontWeight: 800, color, fontSize: 13}}>{t.toFixed(1)}°C</div>}
                      </div>
                    </Tooltip>
                    {w && (
                      <Popup>
                        <div style={{minWidth: 200, fontFamily: 'Inter, sans-serif'}}>
                          <div style={{display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8}}>
                            <span className="material-symbols-outlined" style={{fontSize: 28, color}}>{WEATHER_ICONS[w.weather_code] || 'cloud'}</span>
                            <div>
                              <div style={{fontWeight: 700, fontSize: 15}}>{city.name}</div>
                              <div style={{fontSize: 11, color: '#6b7280', textTransform: 'uppercase', letterSpacing: 0.5}}>{city.type} · {tempBand(t)}</div>
                            </div>
                          </div>
                          <div style={{fontSize: 12, marginBottom: 6, color: '#374151'}}>{WEATHER_DESCRIPTIONS[w.weather_code] || 'Conditions unavailable'}</div>
                          <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, fontSize: 12}}>
                            <div><b style={{color}}>{w.temperature_2m.toFixed(1)}°C</b><div style={{color: '#6b7280', fontSize: 10}}>Temperature</div></div>
                            <div><b>{w.apparent_temperature?.toFixed(1) ?? '—'}°C</b><div style={{color: '#6b7280', fontSize: 10}}>Feels Like</div></div>
                            <div><b>{w.relative_humidity_2m}%</b><div style={{color: '#6b7280', fontSize: 10}}>Humidity</div></div>
                            <div><b>{w.wind_speed_10m?.toFixed(1) ?? '—'} km/h</b><div style={{color: '#6b7280', fontSize: 10}}>Wind</div></div>
                          </div>
                        </div>
                      </Popup>
                    )}
                  </CircleMarker>
                )
              })}
            </MapContainer>

            {loading && (
              <div className="absolute inset-0 flex items-center justify-center bg-surface-container/70 z-[400] pointer-events-none">
                <div className="bg-surface-container-lowest px-5 py-3 rounded-xl flex items-center gap-3 shadow-lg">
                  <span className="material-symbols-outlined animate-spin text-primary">progress_activity</span>
                  <span className="text-sm font-semibold text-on-surface">Fetching live weather…</span>
                </div>
              </div>
            )}
          </div>

          {advisory && (
            <div className={`mt-4 p-4 rounded-xl border-l-4 flex items-start gap-3 ${
              advisory.tone === 'error' ? 'bg-error/5 border-error' :
              advisory.tone === 'warning' ? 'bg-tertiary/5 border-tertiary' :
              'bg-primary/5 border-primary'
            }`}>
              <span className="material-symbols-outlined text-2xl shrink-0" style={{color: advisory.tone === 'error' ? 'var(--error)' : advisory.tone === 'warning' ? 'var(--tertiary)' : 'var(--primary)'}}>
                {advisory.icon}
              </span>
              <div className="flex-grow">
                <p className="text-xs font-bold uppercase tracking-widest mb-1" style={{color: advisory.tone === 'error' ? 'var(--error)' : advisory.tone === 'warning' ? 'var(--tertiary)' : 'var(--primary)'}}>
                  IT Lab Equipment Advisory
                </p>
                <p className="text-sm text-on-surface leading-relaxed">{advisory.msg}</p>
              </div>
            </div>
          )}

          <div className="mt-4 grid grid-cols-2 sm:grid-cols-5 gap-2 text-xs">
            {[
              {color: '#0284c7', label: '<20°C', band: 'Cool'},
              {color: '#16a34a', label: '20–26°C', band: 'Mild'},
              {color: '#eab308', label: '26–32°C', band: 'Warm'},
              {color: '#f97316', label: '32–38°C', band: 'Hot'},
              {color: '#dc2626', label: '>38°C', band: 'Extreme'},
            ].map(l => (
              <div key={l.label} className="flex items-center gap-2 bg-surface-container rounded-lg px-3 py-2">
                <span className="w-3 h-3 rounded-full shrink-0" style={{background: l.color}}></span>
                <div className="leading-tight">
                  <div className="text-on-surface font-bold">{l.label}</div>
                  <div className="text-on-surface-variant text-[10px]">{l.band}</div>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </motion.div>
  )
}

export default MaharashtraWeatherMap
