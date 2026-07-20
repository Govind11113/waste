import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import MaharashtraWeatherMap from './MaharashtraWeatherMap'

vi.mock('framer-motion', () => ({
  motion: {
    /** @param {{ children: import('react').ReactNode, variants?: unknown, initial?: unknown, animate?: unknown } & Record<string, unknown>} props */
    div: ({ children, variants: _variants, initial: _initial, animate: _animate, ...props }) => (
      <div {...props}>{children}</div>
    ),
  },
  useReducedMotion: () => true,
}))

vi.mock('react-leaflet', () => {
  /** @param {{ children: import('react').ReactNode }} props */
  const Container = ({ children }) => <div data-testid="map">{children}</div>
  /** @param {{ children: import('react').ReactNode }} props */
  const ChildContainer = ({ children }) => <div>{children}</div>
  return {
    MapContainer: Container,
    TileLayer: () => <div data-testid="tile-layer" />,
    GeoJSON: () => <div data-testid="boundary" />,
    CircleMarker: ChildContainer,
    Popup: ChildContainer,
    Tooltip: ChildContainer,
    ZoomControl: () => null,
  }
})

describe('MaharashtraWeatherMap fallback', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('network unavailable')))
  })

  it('keeps the map and city locations visible when all live weather calls fail', async () => {
    render(<MaharashtraWeatherMap compact />)

    expect(await screen.findByText(/Live weather is unavailable/i)).toBeVisible()
    expect(screen.getByTestId('map')).toBeVisible()
    expect(screen.getAllByText('Mumbai').length).toBeGreaterThan(0)
    expect(screen.queryByText(/Fetching live weather/i)).not.toBeInTheDocument()
  })
})
