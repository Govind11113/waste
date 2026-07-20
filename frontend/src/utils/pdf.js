const REPORT_COLORS = {
  primary: '#486730',
  secondary: '#00629e',
  text: '#1a1c18',
  muted: '#555555',
  border: '#e2e8f0',
  panel: '#f0f4f8',
  white: '#ffffff',
}

/**
 * @typedef {{ label: string, value: string | number }} ReportRow
 * @typedef {{ heading: string, rows?: ReportRow[], paragraphs?: string[] }} ReportSection
 * @typedef {{ src: string, alt: string, caption?: string }} ReportImage
 * @typedef {{
 *   title: string,
 *   subtitle: string,
 *   summaryLabel: string,
 *   summaryValue: string,
 *   summaryDetail?: string,
 *   image?: ReportImage,
 *   sections: ReportSection[],
 *   footerLeft: string,
 *   footerRight: string,
 * }} ReportConfig
 */

/**
 * Create a styled element while assigning dynamic content through textContent.
 * No report value is ever parsed as HTML.
 *
 * @template {keyof HTMLElementTagNameMap} K
 * @param {K} tag
 * @param {string | number | null | undefined} [text]
 * @param {Partial<CSSStyleDeclaration>} [styles]
 * @returns {HTMLElementTagNameMap[K]}
 */
function createElement(tag, text, styles = {}) {
  const element = document.createElement(tag)
  if (text !== null && text !== undefined) {
    element.textContent = String(text)
  }
  Object.assign(element.style, styles)
  return element
}

/**
 * @param {ReportRow[]} rows
 * @returns {HTMLTableElement}
 */
function createTable(rows) {
  const table = createElement('table', null, {
    width: '100%',
    borderCollapse: 'collapse',
    marginBottom: '24px',
  })

  rows.forEach(({ label, value }) => {
    const row = createElement('tr')
    const labelCell = createElement('td', label, {
      padding: '10px',
      border: `1px solid ${REPORT_COLORS.border}`,
      background: '#fafbfc',
      color: REPORT_COLORS.muted,
      fontWeight: '600',
      width: '40%',
      verticalAlign: 'top',
    })
    const valueCell = createElement('td', value, {
      padding: '10px',
      border: `1px solid ${REPORT_COLORS.border}`,
      color: REPORT_COLORS.text,
      verticalAlign: 'top',
      whiteSpace: 'pre-wrap',
    })
    row.append(labelCell, valueCell)
    table.append(row)
  })

  return table
}

/**
 * Build a printable report using DOM APIs only. Dynamic strings are inserted
 * as text nodes, preventing HTML/script injection from filenames or API data.
 *
 * @param {ReportConfig} config
 * @returns {HTMLDivElement}
 */
export function createPdfReport(config) {
  const root = createElement('div', null, {
    padding: '40px',
    fontFamily: "'Inter', Arial, sans-serif",
    color: REPORT_COLORS.text,
    maxWidth: '800px',
    background: REPORT_COLORS.white,
  })

  const header = createElement('div', null, {
    borderBottom: `3px solid ${REPORT_COLORS.primary}`,
    paddingBottom: '16px',
    marginBottom: '24px',
  })
  header.append(
    createElement('h1', config.title, {
      color: REPORT_COLORS.primary,
      margin: '0 0 4px 0',
      fontSize: '26px',
    }),
    createElement('p', config.subtitle, {
      color: REPORT_COLORS.muted,
      fontSize: '13px',
      margin: '0',
    }),
  )
  root.append(header)

  if (config.image) {
    const imageWrap = createElement('div', null, {
      marginBottom: '24px',
      textAlign: 'center',
    })
    const image = createElement('img')
    image.src = config.image.src
    image.alt = config.image.alt
    Object.assign(image.style, {
      maxWidth: '100%',
      maxHeight: '280px',
      borderRadius: '8px',
      border: `1px solid ${REPORT_COLORS.border}`,
    })
    imageWrap.append(image)
    if (config.image.caption) {
      imageWrap.append(createElement('p', config.image.caption, {
        color: '#888888',
        fontSize: '11px',
        marginTop: '6px',
      }))
    }
    root.append(imageWrap)
  }

  const summary = createElement('div', null, {
    background: REPORT_COLORS.panel,
    padding: '24px',
    borderRadius: '12px',
    marginBottom: '24px',
    textAlign: 'center',
  })
  summary.append(
    createElement('h2', config.summaryLabel, {
      margin: '0 0 6px 0',
      color: REPORT_COLORS.text,
      fontSize: '14px',
      textTransform: 'uppercase',
      letterSpacing: '1px',
    }),
    createElement('div', config.summaryValue, {
      fontSize: '38px',
      fontWeight: '800',
      color: REPORT_COLORS.primary,
    }),
  )
  if (config.summaryDetail) {
    summary.append(createElement('div', config.summaryDetail, {
      fontSize: '13px',
      color: REPORT_COLORS.muted,
      marginTop: '4px',
    }))
  }
  root.append(summary)

  config.sections.forEach((section) => {
    root.append(createElement('h3', section.heading, {
      color: REPORT_COLORS.primary,
      margin: '0 0 12px 0',
      fontSize: '17px',
    }))
    if (section.rows?.length) {
      root.append(createTable(section.rows))
    }
    section.paragraphs?.forEach((paragraph) => {
      root.append(createElement('p', paragraph, {
        margin: '0 0 16px 0',
        padding: '14px',
        border: `1px solid ${REPORT_COLORS.border}`,
        borderRadius: '8px',
        fontSize: '12px',
        lineHeight: '1.5',
        color: REPORT_COLORS.muted,
        whiteSpace: 'pre-wrap',
      }))
    })
  })

  const footer = createElement('div', null, {
    display: 'flex',
    justifyContent: 'space-between',
    gap: '16px',
    paddingTop: '16px',
    borderTop: `1px solid ${REPORT_COLORS.border}`,
    fontSize: '10px',
    color: '#777777',
  })
  footer.append(
    createElement('span', config.footerLeft),
    createElement('span', config.footerRight),
  )
  root.append(footer)

  return root
}

/**
 * Produce a path-safe, bounded PDF filename from user/API-provided text.
 *
 * @param {unknown} value
 * @param {string} reportKind
 * @returns {string}
 */
export function createPdfFilename(value, reportKind) {
  const safeStem = String(value ?? 'device')
    .normalize('NFKD')
    .replace(/[\u0000-\u001f\u007f/\\:*?"<>|]+/g, '_')
    .replace(/[^a-zA-Z0-9._-]+/g, '_')
    .replace(/^[._-]+|[._-]+$/g, '')
    .replace(/_+/g, '_')
    .slice(0, 72) || 'device'
  const safeKind = reportKind.replace(/[^a-zA-Z0-9_-]+/g, '_').slice(0, 32) || 'Report'
  return `${safeStem}_${safeKind}.pdf`
}

/**
 * Lazy-load the heavy PDF renderer only after the user requests an export.
 *
 * @param {HTMLElement} element
 * @param {string} filename
 * @returns {Promise<void>}
 */
export async function exportPdf(element, filename) {
  const { default: html2pdf } = await import('html2pdf.js')
  const options = {
    margin: 0.4,
    filename,
    image: { type: /** @type {'jpeg'} */ ('jpeg'), quality: 0.98 },
    html2canvas: { scale: 2, useCORS: true },
    jsPDF: {
      unit: /** @type {'in'} */ ('in'),
      format: /** @type {'letter'} */ ('letter'),
      orientation: /** @type {'portrait'} */ ('portrait'),
    },
  }
  await html2pdf().from(element).set(options).save()
}
