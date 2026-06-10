import { useState, useRef } from 'react'
import { toast } from 'react-hot-toast'
import html2pdf from 'html2pdf.js'

function Scanner() {
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [previewDataUrl, setPreviewDataUrl] = useState(null)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [isDragging, setIsDragging] = useState(false)
  const fileInputRef = useRef(null)

  const fileToDataUrl = (f) => new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result)
    reader.onerror = reject
    reader.readAsDataURL(f)
  })

  const handleFileSelect = async (e) => {
    const selectedFile = e.target.files[0]
    if (selectedFile) {
      setFile(selectedFile)
      setPreview(URL.createObjectURL(selectedFile))
      setResult(null)
      setError(null)
      try {
        const dataUrl = await fileToDataUrl(selectedFile)
        setPreviewDataUrl(dataUrl)
      } catch {
        setPreviewDataUrl(null)
      }
    }
  }

  const handleDrop = async (e) => {
    e.preventDefault()
    setIsDragging(false)
    const droppedFile = e.dataTransfer.files[0]
    if (droppedFile && droppedFile.type.startsWith('image/')) {
      setFile(droppedFile)
      setPreview(URL.createObjectURL(droppedFile))
      setResult(null)
      setError(null)
      try {
        const dataUrl = await fileToDataUrl(droppedFile)
        setPreviewDataUrl(dataUrl)
      } catch {
        setPreviewDataUrl(null)
      }
    }
  }

  const handleDragOver = (e) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (e) => {
    e.preventDefault()
    setIsDragging(false)
  }

  const handleAnalyze = async () => {
    if (!file) return

    setLoading(true)
    setError(null)
    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await fetch('/api/v1/classifier/scan', {
        method: 'POST',
        body: formData
      })
      if (!response.ok) throw new Error('Classification failed. Please try again.')
      const data = await response.json()
      setResult(data)
    } catch (err) {
      const message = err.message || 'Failed to analyze image. Please try again.'
      setError(message)
      toast.error(message)
    } finally {
      setLoading(false)
    }
  }

  const handleReset = () => {
    setFile(null)
    setPreview(null)
    setPreviewDataUrl(null)
    setResult(null)
    setError(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const handleDownloadPDF = () => {
    if (!result || result.entity === 'Unrecognized') return

    const generatedAt = new Date().toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })
    const confidencePct = (result.confidence * 100).toFixed(1)
    const hazardColor = result.hazard_level === 'Hazardous' ? '#ba1a1a' : '#486730'
    const conditionLabel = result.condition.charAt(0).toUpperCase() + result.condition.slice(1)
    const modelLabel = result.model_used === 'local'
      ? 'CLIP Zero-Shot Classification'
      : result.model_used === 'siglip'
        ? 'SigLIP Zero-Shot Classification'
        : result.model_used?.includes('low_confidence')
          ? 'Zero-Shot (Low Confidence)'
          : 'Zero-Shot Classification'

    const element = document.createElement('div')
    element.innerHTML = `
      <div style="padding: 40px; font-family: 'Inter', Arial, sans-serif; color: #1a1c18; max-width: 800px;">
        <div style="border-bottom: 3px solid #486730; padding-bottom: 16px; margin-bottom: 24px;">
          <h1 style="color: #486730; margin: 0 0 4px 0; font-size: 26px;">E-Waste Management System</h1>
          <p style="color: #555; font-size: 13px; margin: 0;">Maharashtra Educational Sector — Device Classification Report</p>
        </div>

        ${previewDataUrl ? `
          <div style="margin-bottom: 24px; text-align: center;">
            <img src="${previewDataUrl}" alt="Analyzed device"
                 style="max-width: 100%; max-height: 280px; border-radius: 8px; border: 1px solid #ddd;" />
            <p style="color: #888; font-size: 11px; margin-top: 6px;">Submitted image: ${file?.name || 'device.jpg'}</p>
          </div>
        ` : ''}

        <div style="background: #f0f4f8; padding: 24px; border-radius: 12px; margin-bottom: 24px;">
          <h2 style="margin: 0 0 6px 0; color: #1a1c18; font-size: 14px; text-transform: uppercase; letter-spacing: 1px;">Identified Device</h2>
          <div style="font-size: 32px; font-weight: 800; color: #486730; margin-bottom: 8px;">${result.entity}</div>
          <div style="font-size: 13px; color: #555;">Category: ${result.group}</div>
          <div style="margin-top: 16px;">
            <div style="font-size: 12px; color: #555; margin-bottom: 4px;">Confidence: <strong>${confidencePct}%</strong></div>
            <div style="background: #e2e8f0; height: 10px; border-radius: 5px; overflow: hidden;">
              <div style="background: #486730; width: ${confidencePct}%; height: 100%;"></div>
            </div>
          </div>
        </div>

        <table style="width: 100%; border-collapse: collapse; margin-bottom: 24px;">
          <tr>
            <td style="padding: 12px; border: 1px solid #e2e8f0; background: #fafbfc; font-weight: 600; color: #555; width: 40%;">Waste Status</td>
            <td style="padding: 12px; border: 1px solid #e2e8f0; color: ${result.waste_status === 'E-Waste' ? '#ba1a1a' : '#486730'}; font-weight: 700;">${result.waste_status}</td>
          </tr>
          <tr>
            <td style="padding: 12px; border: 1px solid #e2e8f0; background: #fafbfc; font-weight: 600; color: #555;">Recyclable</td>
            <td style="padding: 12px; border: 1px solid #e2e8f0; color: ${result.recyclable ? '#486730' : '#ba1a1a'}; font-weight: 700;">
              ${result.recyclable ? `Yes — ${result.recyclability} material recovery` : 'No'}
            </td>
          </tr>
          <tr>
            <td style="padding: 12px; border: 1px solid #e2e8f0; background: #fafbfc; font-weight: 600; color: #555;">Hazard Level</td>
            <td style="padding: 12px; border: 1px solid #e2e8f0; color: ${hazardColor}; font-weight: 700;">${result.hazard_level}</td>
          </tr>
          <tr>
            <td style="padding: 12px; border: 1px solid #e2e8f0; background: #fafbfc; font-weight: 600; color: #555;">Condition</td>
            <td style="padding: 12px; border: 1px solid #e2e8f0;">${conditionLabel}</td>
          </tr>
          <tr>
            <td style="padding: 12px; border: 1px solid #e2e8f0; background: #fafbfc; font-weight: 600; color: #555;">CO₂ Saved by Recycling</td>
            <td style="padding: 12px; border: 1px solid #e2e8f0; color: #486730; font-weight: 700;">${result.co2_delta} kg</td>
          </tr>
          <tr>
            <td style="padding: 12px; border: 1px solid #e2e8f0; background: #fafbfc; font-weight: 600; color: #555;">Model Used</td>
            <td style="padding: 12px; border: 1px solid #e2e8f0;">${modelLabel}</td>
          </tr>
        </table>

        <div style="padding: 20px; border-left: 4px solid #486730; background: #f0f4f8; border-radius: 8px; margin-bottom: 24px;">
          <h3 style="margin: 0 0 8px 0; color: #486730; font-size: 14px; text-transform: uppercase; letter-spacing: 1px;">Disposal Recommendation</h3>
          <p style="margin: 0; line-height: 1.6; color: #1a1c18;">${result.disposal_advice}</p>
        </div>

        <div style="padding: 16px; border: 1px solid #e2e8f0; border-radius: 8px; margin-bottom: 32px; background: #fff;">
          <h3 style="margin: 0 0 8px 0; color: #555; font-size: 12px; text-transform: uppercase; letter-spacing: 1px;">Compliance Note</h3>
          <p style="margin: 0; font-size: 12px; line-height: 1.5; color: #555;">
            Under the E-Waste (Management) Rules, 2022, educational institutions in Maharashtra must channel
            end-of-life electronics through authorized recyclers and maintain audit-ready disposal records.
          </p>
        </div>

        <div style="display: flex; justify-content: space-between; padding-top: 16px; border-top: 1px solid #e2e8f0; font-size: 10px; color: #999;">
          <span>Generated: ${generatedAt}</span>
          <span>Analysis ID: ${result.analysis_id?.slice(0, 13) || 'N/A'}</span>
        </div>
      </div>
    `

    const opt = {
      margin: 0.4,
      filename: `${result.entity.replace(/\s|\//g, '_')}_Scan_Report.pdf`,
      image: { type: 'jpeg', quality: 0.98 },
      html2canvas: { scale: 2, useCORS: true },
      jsPDF: { unit: 'in', format: 'letter', orientation: 'portrait' }
    }

    html2pdf().from(element).set(opt).save()
    toast.success('Report downloaded')
  }

  const isUnrecognized = result?.entity === 'Unrecognized'

  const getConditionIcon = (condition) => {
    switch (condition) {
      case 'burnt': return { icon: 'local_fire_department', color: 'text-error' }
      case 'damaged': return { icon: 'warning', color: 'text-tertiary' }
      default: return { icon: 'check_circle', color: 'text-primary' }
    }
  }

  return (
    <div className="pt-32 pb-20 px-8 max-w-7xl mx-auto page-transition">
      <header className="mb-12 animate-fade-in-down">
        <h1 className="text-5xl font-extrabold text-on-surface tracking-tight mb-4">E-Waste Classifier</h1>
        <p className="text-xl text-on-surface-variant max-w-2xl">Upload device images for instant classification using CLIP/SigLIP zero-shot vision models — no training required.</p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <section className="animate-fade-in-up stagger-1">
          <div
            onClick={() => !result && fileInputRef.current?.click()}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            className={`bg-surface-container-lowest border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all duration-300 ${
              isDragging
                ? 'border-secondary bg-secondary/5 scale-[1.02] shadow-lg'
                : result
                  ? 'border-primary/30 bg-primary/5'
                  : 'border-outline-variant hover:border-secondary hover:shadow-lg hover:scale-[1.01]'
            }`}
          >
            {preview ? (
              <div className="animate-image-reveal">
                <img src={preview} alt="Preview" className="w-full h-64 object-contain rounded-lg mb-4" />
                <p className="text-sm text-on-surface font-medium">{file?.name}</p>
                {result && !isUnrecognized && (
                  <div className="mt-3 inline-flex items-center gap-2 px-3 py-1 bg-primary/10 rounded-full animate-fade-in">
                    <span className="material-symbols-outlined text-primary text-sm">check_circle</span>
                    <span className="text-xs font-bold text-primary">Analyzed</span>
                  </div>
                )}
                {isUnrecognized && (
                  <div className="mt-3 inline-flex items-center gap-2 px-3 py-1 bg-error/10 rounded-full animate-fade-in">
                    <span className="material-symbols-outlined text-error text-sm">help</span>
                    <span className="text-xs font-bold text-error">Not Recognized</span>
                  </div>
                )}
              </div>
            ) : (
              <>
                <span className={`material-symbols-outlined text-6xl mb-4 transition-all duration-300 ${
                  isDragging ? 'text-secondary scale-110' : 'text-outline'
                }`}>
                  {isDragging ? 'file_download' : 'cloud_upload'}
                </span>
                <p className="text-lg font-semibold text-on-surface mb-2">
                  {isDragging ? 'Drop image here' : 'Drop image here or click to upload'}
                </p>
                <p className="text-sm text-outline">Supports JPG, PNG up to 10MB</p>
              </>
            )}
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={handleFileSelect}
              className="hidden"
            />
          </div>

          {preview && !result && (
            <div className="mt-4 flex gap-3 animate-fade-in-up">
              <button
                onClick={handleAnalyze}
                disabled={loading}
                className="flex-1 bg-primary text-on-primary py-3.5 rounded-xl font-bold hover:opacity-90 transition-all disabled:opacity-50 hover:-translate-y-0.5 hover:shadow-lg active:scale-[0.98] btn-ripple"
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <span className="material-symbols-outlined animate-spin text-lg">progress_activity</span>
                    Analyzing...
                  </span>
                ) : 'Analyze Image'}
              </button>
              <button
                onClick={handleReset}
                disabled={loading}
                className="px-6 border border-outline text-on-surface py-3.5 rounded-xl font-bold hover:bg-surface-container transition-all disabled:opacity-50 active:scale-[0.98]"
              >
                Reset
              </button>
            </div>
          )}

          {result && !isUnrecognized && (
            <div className="mt-4 grid grid-cols-2 gap-3 animate-fade-in-up">
              <button
                onClick={handleDownloadPDF}
                className="bg-primary text-on-primary py-3.5 rounded-xl font-bold hover:opacity-90 transition-all active:scale-[0.98] hover:-translate-y-0.5 hover:shadow-lg btn-ripple flex items-center justify-center gap-2"
              >
                <span className="material-symbols-outlined text-lg">download</span>
                Download Report
              </button>
              <button
                onClick={handleReset}
                className="border-2 border-primary text-primary py-3.5 rounded-xl font-bold hover:bg-primary/5 transition-all active:scale-[0.98] hover:-translate-y-0.5 flex items-center justify-center gap-2"
              >
                <span className="material-symbols-outlined text-lg">add_a_photo</span>
                New Scan
              </button>
            </div>
          )}

          {result && isUnrecognized && (
            <div className="mt-4 flex gap-3 animate-fade-in-up">
              <button
                onClick={handleReset}
                className="flex-1 bg-primary text-on-primary py-3.5 rounded-xl font-bold hover:opacity-90 transition-all active:scale-[0.98] hover:-translate-y-0.5 flex items-center justify-center gap-2"
              >
                <span className="material-symbols-outlined text-lg">restart_alt</span>
                Try Another Image
              </button>
            </div>
          )}

          {error && (
            <div className="mt-4 p-4 bg-error-container rounded-xl flex items-center gap-3 animate-scale-in">
              <span className="material-symbols-outlined text-on-error-container">error</span>
              <span className="text-sm font-medium text-on-error-container">{error}</span>
            </div>
          )}

          {loading && (
            <div className="mt-6 bg-surface-container-lowest p-8 rounded-xl animate-fade-in">
              <div className="flex flex-col items-center justify-center gap-4">
                <span className="material-symbols-outlined text-5xl text-primary animate-spin">analytics</span>
                <div className="text-center">
                  <p className="text-lg font-semibold text-on-surface">Analyzing image...</p>
                  <p className="text-sm text-on-surface-variant mt-1">Running zero-shot image classification</p>
                </div>
                <div className="w-full bg-surface-container rounded-full h-2 overflow-hidden mt-4">
                  <div className="bg-primary h-2 rounded-full animate-pulse" style={{width: '75%', transition: 'width 2s ease'}}></div>
                </div>
              </div>
            </div>
          )}
        </section>

        <section className="space-y-6 animate-fade-in-up stagger-2">
          {result && isUnrecognized && (
            <div className="bg-error-container/40 border-2 border-error/30 p-8 rounded-xl animate-scale-in-bounce card-shadow">
              <div className="flex items-start gap-4">
                <div className="w-14 h-14 rounded-xl bg-error/10 flex items-center justify-center shrink-0">
                  <span className="material-symbols-outlined text-error text-3xl">
                    {result.rejection_reason === 'non_electronic' ? 'not_interested' : 'image_not_supported'}
                  </span>
                </div>
                <div className="flex-1">
                  <h3 className="text-xl font-bold text-on-surface mb-2">
                    {result.rejection_reason === 'non_electronic' ? 'Not an Electronic Device' : 'Image Not Recognized'}
                  </h3>
                  <p className="text-on-surface-variant mb-4 leading-relaxed">
                    {result.condition || "The classifier couldn't confidently identify the device in this image."}
                  </p>
                  <div className="bg-surface-container-lowest rounded-lg p-4 space-y-2">
                    <p className="text-sm font-semibold text-on-surface">
                      {result.rejection_reason === 'non_electronic'
                        ? 'What to upload:'
                        : 'Tips for a better scan:'}
                    </p>
                    <ul className="text-sm text-on-surface-variant space-y-1.5 list-disc pl-5">
                      {result.rejection_reason === 'non_electronic' ? (
                        <>
                          <li>Laptops, desktops, or tablets</li>
                          <li>Phones, smartwatches, or earbuds</li>
                          <li>Monitors, keyboards, or mice</li>
                          <li>Printers, projectors, or routers</li>
                          <li>ACs, TVs, microwaves, or cameras</li>
                        </>
                      ) : (
                        <>
                          <li>Use a well-lit environment</li>
                          <li>Make sure the device fills most of the frame</li>
                          <li>Avoid blurry or partial shots</li>
                          <li>Use a plain, contrasting background</li>
                        </>
                      )}
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          )}

          {result && !isUnrecognized && (
            <div className="bg-surface-container-lowest p-6 rounded-xl animate-scale-in-bounce hover-lift card-shadow">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                    <span className="material-symbols-outlined text-primary">fact_check</span>
                  </div>
                  <h3 className="text-xl font-bold text-on-surface">Analysis Results</h3>
                </div>
                {result.model_used === 'clip_fallback' && (
                  <span className="px-3 py-1 bg-secondary/10 text-secondary rounded-full text-xs font-bold">
                    Fallback model
                  </span>
                )}
              </div>

              <div className="space-y-3">
                <div className="flex justify-between items-center p-3.5 bg-surface-container rounded-xl">
                  <span className="text-on-surface-variant text-sm">Device Type</span>
                  <span className="font-bold text-on-surface text-lg">{result.entity}</span>
                </div>
                <div className="flex justify-between items-center p-3.5 bg-surface-container rounded-xl">
                  <span className="text-on-surface-variant text-sm">Category</span>
                  <span className="font-semibold text-on-surface">{result.group}</span>
                </div>
                <div className="flex justify-between items-center p-3.5 bg-surface-container rounded-xl">
                  <span className="text-on-surface-variant text-sm">Waste Status</span>
                  <span className={`font-bold ${result.waste_status === 'E-Waste' ? 'text-error' : 'text-primary'}`}>
                    {result.waste_status}
                  </span>
                </div>
                <div className="flex justify-between items-center p-3.5 bg-surface-container rounded-xl">
                  <span className="text-on-surface-variant text-sm">Recyclable</span>
                  <span className={`font-bold flex items-center gap-1.5 ${result.recyclable ? 'text-primary' : 'text-error'}`}>
                    <span className="material-symbols-outlined text-lg">
                      {result.recyclable ? 'recycling' : 'block'}
                    </span>
                    {result.recyclable ? `Yes — ${result.recyclability} recovery` : 'No'}
                  </span>
                </div>
                <div className="flex justify-between items-center p-3.5 bg-surface-container rounded-xl">
                  <span className="text-on-surface-variant text-sm">Hazard Level</span>
                  <span className={`font-bold ${result.hazard_level === 'Hazardous' ? 'text-error' : 'text-primary'}`}>
                    {result.hazard_level}
                  </span>
                </div>
                <div className="flex justify-between items-center p-3.5 bg-surface-container rounded-xl">
                  <span className="text-on-surface-variant text-sm">Confidence</span>
                  <div className="flex items-center gap-2">
                    <div className="w-20 h-2 bg-surface-container-highest rounded-full overflow-hidden">
                      <div className="h-full bg-primary rounded-full transition-all duration-1000" style={{width: `${result.confidence * 100}%`}}></div>
                    </div>
                    <span className="font-bold text-on-surface">{(result.confidence * 100).toFixed(1)}%</span>
                  </div>
                </div>
                <div className="flex justify-between items-center p-3.5 bg-surface-container rounded-xl">
                  <span className="text-on-surface-variant text-sm">Condition</span>
                  <span className={`font-bold capitalize flex items-center gap-1.5 ${getConditionIcon(result.condition).color}`}>
                    <span className="material-symbols-outlined text-lg">{getConditionIcon(result.condition).icon}</span>
                    {result.condition}
                  </span>
                </div>
                <div className="flex justify-between items-center p-3.5 bg-primary/5 border border-primary/20 rounded-xl">
                  <span className="text-on-surface-variant text-sm">CO₂ Saved by Recycling</span>
                  <span className="font-black text-primary text-lg">{result.co2_delta} kg</span>
                </div>
              </div>

              {result.disposal_advice && (
                <div className="mt-4 p-4 bg-secondary/5 border-l-4 border-secondary rounded-r-lg">
                  <p className="text-xs font-bold uppercase tracking-widest text-secondary mb-1">Disposal Advice</p>
                  <p className="text-sm text-on-surface leading-relaxed">{result.disposal_advice}</p>
                </div>
              )}

              <div className="mt-4 pt-4 border-t border-outline-variant/20 flex items-center justify-between text-xs text-outline">
                <span>Processing: {result.processing_time}s</span>
                <span>ID: {result.analysis_id?.slice(0, 8)}</span>
              </div>
            </div>
          )}

          <div className="bg-surface-container-low p-6 rounded-xl hover-lift card-shadow">
            <h3 className="text-lg font-bold text-on-surface mb-4">Supported Devices</h3>
            <div className="flex flex-wrap gap-2">
              {['Motherboard', 'Hard Disk / SSD', 'Monitor', 'Mouse', 'Keyboard', 'Smartphone', 'Computer', 'Printer', 'Projector', 'Router / Switch', 'Air Conditioner', 'Microwave', 'Television', 'Camera', 'Smartwatch', 'Laptop'].map((cls) => (
                <span key={cls} className="bg-surface-container-highest px-3 py-1.5 rounded-full text-sm text-on-surface hover:bg-primary hover:text-on-primary transition-all duration-300 cursor-default hover:scale-105 transform">
                  {cls}
                </span>
              ))}
            </div>
            <p className="text-xs text-outline mt-3">All categories classified via SigLIP zero-shot vision model — no training required.</p>
          </div>

          <div className="bg-surface-container-low p-6 rounded-xl hover-lift card-shadow">
            <h3 className="text-lg font-bold text-on-surface mb-4">How It Works</h3>              <div className="space-y-3">
              <div className="flex items-start gap-3">
                <div className="w-7 h-7 rounded-full bg-primary/10 flex items-center justify-center shrink-0 mt-0.5">
                  <span className="text-xs font-bold text-primary">1</span>
                </div>
                <p className="text-sm text-on-surface-variant">Upload a clear photo of the electronic device</p>
              </div>
              <div className="flex items-start gap-3">
                <div className="w-7 h-7 rounded-full bg-primary/10 flex items-center justify-center shrink-0 mt-0.5">
                  <span className="text-xs font-bold text-primary">2</span>
                </div>
                <p className="text-sm text-on-surface-variant">3-stage pipeline: quality check → electronics gate → device classification</p>
              </div>
              <div className="flex items-start gap-3">
                <div className="w-7 h-7 rounded-full bg-primary/10 flex items-center justify-center shrink-0 mt-0.5">
                  <span className="text-xs font-bold text-primary">3</span>
                </div>
                <p className="text-sm text-on-surface-variant">Non-electronic images and poor quality photos are automatically rejected</p>
              </div>
              <div className="flex items-start gap-3">
                <div className="w-7 h-7 rounded-full bg-primary/10 flex items-center justify-center shrink-0 mt-0.5">
                  <span className="text-xs font-bold text-primary">4</span>
                </div>
                <p className="text-sm text-on-surface-variant">Get device details, hazard level, CO₂ impact, and disposal recommendation</p>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}

export default Scanner
