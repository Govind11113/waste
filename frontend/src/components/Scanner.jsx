import { useState, useRef, useEffect } from 'react'
import { motion } from 'framer-motion'
import { toast } from 'react-hot-toast'
import { createPdfFilename, createPdfReport, exportPdf } from '../utils/pdf'
import { validateImageFile, uploadWithProgress, getRateLimitInfo } from '../utils/apiUtils'
import AnimatedPage from './AnimatedPage'
import { scaleReveal, hoverLift, tapShrink } from '../utils/motion'
import { useAuth } from '@clerk/clerk-react'

/**
 * @typedef {{
 *   entity: string,
 *   confidence: number,
 *   condition: string,
 *   model_used: string,
 *   group: string,
 *   waste_status: string,
 *   recyclable: boolean,
 *   recyclability: string,
 *   co2_delta: number,
 *   disposal_advice: string,
 *   analysis_id?: string,
 *   processing_time: number,
 *   rejection_reason?: string,
 * }} ScannerResult
 */

function Scanner() {
  const [file, setFile] = useState(/** @type {File | null} */ (null))
  const [preview, setPreview] = useState(/** @type {string | null} */ (null))
  const [previewDataUrl, setPreviewDataUrl] = useState(/** @type {string | null} */ (null))
  const [result, setResult] = useState(/** @type {ScannerResult | null} */ (null))
  const [loading, setLoading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [error, setError] = useState(/** @type {string | null} */ (null))
  const [isDragging, setIsDragging] = useState(false)
  const [rateLimit, setRateLimit] = useState(/** @type {{ remaining: number | null, reset: number | null } | null} */ (null))
  const fileInputRef = useRef(/** @type {HTMLInputElement | null} */ (null))
  const previewUrlRef = useRef(/** @type {string | null} */ (null))
  const uploadControllerRef = useRef(/** @type {AbortController | null} */ (null))
  const selectionSequenceRef = useRef(0)
  const { getToken } = useAuth()

  /** @param {string | null} newUrl */
  const setPreviewUrl = (newUrl) => {
    if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current)
    previewUrlRef.current = newUrl
    setPreview(newUrl)
  }

  useEffect(() => () => {
    uploadControllerRef.current?.abort()
    if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current)
  }, [])

  /** @param {File} selectedFile @returns {Promise<string>} */
  const fileToDataUrl = (selectedFile) => new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      if (typeof reader.result === 'string') resolve(reader.result)
      else reject(new Error('Could not create image preview'))
    }
    reader.onerror = () => reject(reader.error ?? new Error('Could not read image'))
    reader.readAsDataURL(selectedFile)
  })

  /** @param {File} selectedFile */
  const selectFile = async (selectedFile) => {
    const sequence = ++selectionSequenceRef.current
    const validation = await validateImageFile(selectedFile)
    if (sequence !== selectionSequenceRef.current) return
    if (!validation.valid) {
      toast.error(validation.error || 'Invalid image')
      return
    }

    uploadControllerRef.current?.abort()
    uploadControllerRef.current = null
    setLoading(false)
    setUploadProgress(0)
    setFile(selectedFile)
    setPreviewUrl(URL.createObjectURL(selectedFile))
    setPreviewDataUrl(null)
    setResult(null)
    setError(null)

    try {
      const dataUrl = await fileToDataUrl(selectedFile)
      if (sequence === selectionSequenceRef.current) setPreviewDataUrl(dataUrl)
    } catch {
      if (sequence === selectionSequenceRef.current) setPreviewDataUrl(null)
    }
  }

  /** @param {import('react').ChangeEvent<HTMLInputElement>} event */
  const handleFileSelect = (event) => {
    const selectedFile = event.target.files?.[0]
    if (selectedFile) selectFile(selectedFile)
  }

  /** @param {import('react').DragEvent<HTMLDivElement>} event */
  const handleDrop = (event) => {
    event.preventDefault()
    setIsDragging(false)
    const droppedFile = event.dataTransfer.files?.[0]
    if (droppedFile && !loading && !result) selectFile(droppedFile)
  }

  /** @param {import('react').DragEvent<HTMLDivElement>} event */
  const handleDragOver = (event) => {
    event.preventDefault()
    if (!loading && !result) setIsDragging(true)
  }

  /** @param {import('react').DragEvent<HTMLDivElement>} event */
  const handleDragLeave = (event) => {
    event.preventDefault()
    setIsDragging(false)
  }

  const openFilePicker = () => {
    if (!loading && !result) fileInputRef.current?.click()
  }

  /** @param {import('react').KeyboardEvent<HTMLDivElement>} event */
  const handleUploadKeyDown = (event) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      openFilePicker()
    }
  }

  const handleAnalyze = async () => {
    if (!file || loading) return

    uploadControllerRef.current?.abort()
    const controller = new AbortController()
    uploadControllerRef.current = controller
    setLoading(true)
    setError(null)
    setUploadProgress(0)
    const formData = new FormData()
    formData.append('file', file)

    try {
      const token = await getToken()
      if (controller.signal.aborted) throw new DOMException('Upload aborted', 'AbortError')
      const response = await uploadWithProgress(
        '/api/v1/classifier/scan',
        formData,
        token,
        (progress) => {
          if (uploadControllerRef.current === controller) setUploadProgress(progress)
        },
        { signal: controller.signal, timeoutMs: 180_000 },
      )

      const data = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(data.detail || `Classification failed (${response.status})`)
      if (uploadControllerRef.current !== controller) return

      const rateLimitInfo = getRateLimitInfo(response)
      if (rateLimitInfo.remaining !== null) setRateLimit(rateLimitInfo)
      setResult(data)
      setUploadProgress(100)
    } catch (caught) {
      if (controller.signal.aborted || (caught instanceof DOMException && caught.name === 'AbortError')) return
      const message = caught instanceof Error ? caught.message : 'Failed to analyze image. Please try again.'
      setError(message)
      toast.error(message)
    } finally {
      if (uploadControllerRef.current === controller) {
        uploadControllerRef.current = null
        setLoading(false)
      }
    }
  }

  const handleReset = () => {
    selectionSequenceRef.current += 1
    uploadControllerRef.current?.abort()
    uploadControllerRef.current = null
    setLoading(false)
    setUploadProgress(0)
    setIsDragging(false)
    setFile(null)
    setPreviewUrl(null)
    setPreviewDataUrl(null)
    setResult(null)
    setRateLimit(null)
    setError(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const handleDownloadPDF = async () => {
    if (!result || result.entity === 'Unrecognized') return

    const userLocale = navigator.language || 'en-IN'
    const generatedAt = new Date().toLocaleString(userLocale, { dateStyle: 'medium', timeStyle: 'short' })
    const confidencePct = (Number(result.confidence) * 100).toFixed(1)
    const condition = String(result.condition || 'unknown')
    const conditionLabel = condition.charAt(0).toUpperCase() + condition.slice(1)
    const modelLabel = result.model_used === 'local'
      ? 'CLIP zero-shot classification'
      : result.model_used === 'siglip'
        ? 'SigLIP zero-shot classification'
        : String(result.model_used || '').includes('low_confidence')
          ? 'Zero-shot classification (low confidence)'
          : 'Zero-shot classification'
    const imageName = file?.name || 'device image'
    const report = createPdfReport({
      title: 'E-Waste Classification Report',
      subtitle: 'Maharashtra Educational Sector — Device Classification',
      summaryLabel: 'Identified device',
      summaryValue: String(result.entity),
      summaryDetail: `Category ${result.group} · Confidence ${confidencePct}%`,
      image: typeof previewDataUrl === 'string'
        ? {
            src: previewDataUrl,
            alt: `${result.entity} device in ${condition.toLowerCase()} condition`,
            caption: `Analyzed file: ${imageName}`,
          }
        : undefined,
      sections: [
        {
          heading: 'Classification details',
          rows: [
            { label: 'Waste status', value: result.waste_status },
            { label: 'Recyclable', value: result.recyclable ? `Yes — ${result.recyclability} material recovery` : 'No' },
            { label: 'Condition heuristic', value: conditionLabel },
            { label: 'Indicative material-recovery CO₂ estimate', value: `${result.co2_delta} kg` },
            { label: 'Model used', value: modelLabel },
          ],
        },
        {
          heading: 'Disposal recommendation',
          paragraphs: [
            String(result.disposal_advice || 'Consult an authorized recycler for device-specific handling.'),
            'The classification is zero-shot model inference and the condition label is a global-image heuristic. This report is decision support, not a certified inspection or measured recycling outcome.',
            'Under the E-Waste (Management) Rules, 2022, institutions should channel end-of-life electronics through authorized recyclers and retain appropriate disposal records.',
          ],
        },
      ],
      footerLeft: `Generated: ${generatedAt}`,
      footerRight: `Analysis ID: ${String(result.analysis_id || 'N/A').slice(0, 13)}`,
    })

    try {
      await exportPdf(report, createPdfFilename(result.entity, 'Scan_Report'))
      toast.success('Report downloaded')
    } catch {
      toast.error('Could not generate the PDF report')
    }
  }

  const isUnrecognized = result?.entity === 'Unrecognized'

  /** @param {string} condition */
  const getConditionIcon = (condition) => {
    switch (condition) {
      case 'burnt': return { icon: 'local_fire_department', color: 'text-error' }
      case 'damaged': return { icon: 'warning', color: 'text-tertiary' }
      default: return { icon: 'check_circle', color: 'text-primary' }
    }
  }

  return (
    <AnimatedPage>
    <div className="pt-32 pb-20 px-8 max-w-7xl mx-auto page-transition">
      <header className="mb-12 animate-fade-in-down">
        <h1 className="text-5xl font-extrabold text-on-surface tracking-tight mb-4">E-Waste Classifier</h1>
        <p className="text-xl text-on-surface-variant max-w-2xl">Upload device images for instant classification using CLIP/SigLIP zero-shot vision models — no training required.</p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <section className="animate-fade-in-up stagger-1">
          <div
            role="button"
            tabIndex={0}
            aria-label={result ? 'Image already analyzed. Choose New Scan to upload another image.' : 'Upload a device image'}
            aria-describedby={preview ? undefined : 'scanner-upload-help'}
            aria-disabled={loading || Boolean(result)}
            onClick={openFilePicker}
            onKeyDown={handleUploadKeyDown}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            className={`bg-surface-container-lowest border-2 border-dashed rounded-xl p-12 text-center transition-all duration-300 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 ${
              loading || result ? 'cursor-default' : 'cursor-pointer'
            } ${
              isDragging
                ? 'border-secondary bg-secondary/5 scale-[1.02] shadow-lg'
                : result
                  ? 'border-primary/30 bg-primary/5'
                  : 'border-outline-variant hover:border-secondary hover:shadow-lg hover:scale-[1.01]'
            }`}
          >
            {preview ? (
              <div className="animate-image-reveal">
                <img src={preview} alt={`Selected device: ${file?.name || 'image preview'}`} className="w-full h-64 object-contain rounded-lg mb-4" />
                <p className="text-sm text-on-surface font-medium">{file?.name}</p>
                {result && !isUnrecognized && (
                  <div className="mt-3 inline-flex items-center gap-2 px-3 py-1 bg-primary/10 rounded-full animate-fade-in">
                    <span className="material-symbols-outlined text-primary text-sm" aria-hidden="true">check_circle</span>
                    <span className="text-xs font-bold text-primary">Analyzed</span>
                  </div>
                )}
                {isUnrecognized && (
                  <div className="mt-3 inline-flex items-center gap-2 px-3 py-1 bg-error/10 rounded-full animate-fade-in">
                    <span className="material-symbols-outlined text-error text-sm" aria-hidden="true">help</span>
                    <span className="text-xs font-bold text-error">Not Recognized</span>
                  </div>
                )}
              </div>
            ) : (
              <>
                <span className={`material-symbols-outlined text-6xl mb-4 transition-all duration-300 ${
                  isDragging ? 'text-secondary scale-110' : 'text-outline'
                }`} aria-hidden="true">
                  {isDragging ? 'file_download' : 'cloud_upload'}
                </span>
                <p className="text-lg font-semibold text-on-surface mb-2">
                  {isDragging ? 'Drop image here' : 'Drop image here, click, or press Enter to upload'}
                </p>
                <p id="scanner-upload-help" className="text-sm text-outline">JPEG, PNG, or WebP up to 10MB; minimum dimension 160px.</p>
              </>
            )}
            <input
              id="scanner-file-input"
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              aria-label="Choose a device image"
              tabIndex={-1}
              onClick={(event) => event.stopPropagation()}
              onChange={handleFileSelect}
              className="sr-only"
            />
          </div>

          {preview && !result && (
            <div className="mt-4 animate-fade-in-up">
              {uploadProgress > 0 && uploadProgress < 100 && (
                <div className="mb-3">
                  <div className="flex justify-between text-sm text-on-surface-variant mb-1">
                    <span>Uploading...</span>
                    <span>{uploadProgress}%</span>
                  </div>
                  <div
                    className="h-2 bg-surface-container rounded-full overflow-hidden"
                    role="progressbar"
                    aria-label="Image upload progress"
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-valuenow={uploadProgress}
                  >
                    <div
                      className="h-full bg-primary transition-all duration-300"
                      style={{ width: `${uploadProgress}%` }}
                    />
                  </div>
                </div>
              )}

              <div className="flex gap-3">
                <motion.button
                  whileHover={hoverLift}
                  whileTap={tapShrink}
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
                </motion.button>
                <motion.button
                  whileHover={hoverLift}
                  whileTap={tapShrink}
                  onClick={handleReset}
                  disabled={loading}
                  className="px-6 border border-outline text-on-surface py-3.5 rounded-xl font-bold hover:bg-surface-container transition-all disabled:opacity-50 active:scale-[0.98]"
                >
                  Reset
                </motion.button>
              </div>

              {rateLimit && rateLimit.remaining !== null && (
                <div className="mt-3 text-sm text-on-surface-variant text-center">
                  {rateLimit.remaining} scans remaining this minute
                </div>
              )}
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
              <motion.button
                whileHover={hoverLift}
                whileTap={tapShrink}
                onClick={handleReset}
                className="border-2 border-primary text-primary py-3.5 rounded-xl font-bold hover:bg-primary/5 transition-all active:scale-[0.98] hover:-translate-y-0.5 flex items-center justify-center gap-2"
              >
                <span className="material-symbols-outlined text-lg">add_a_photo</span>
                New Scan
              </motion.button>
            </div>
          )}

          {result && isUnrecognized && (
            <div className="mt-4 flex gap-3 animate-fade-in-up">
              <motion.button
                whileHover={hoverLift}
                whileTap={tapShrink}
                onClick={handleReset}
                className="flex-1 bg-primary text-on-primary py-3.5 rounded-xl font-bold hover:opacity-90 transition-all active:scale-[0.98] hover:-translate-y-0.5 flex items-center justify-center gap-2"
              >
                <span className="material-symbols-outlined text-lg">restart_alt</span>
                Try Another Image
              </motion.button>
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
                          <li>Laptops or desktop computers</li>
                          <li>Smartphones or smartwatches</li>
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
            <motion.div
              variants={scaleReveal}
              initial="hidden"
              animate="visible"
              className="bg-surface-container-lowest p-6 rounded-xl animate-scale-in-bounce hover-lift card-shadow"
            >
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
                  <span className="text-on-surface-variant text-sm">Indicative Recovery CO₂ Estimate</span>
                  <span className="font-black text-primary text-lg">{result.co2_delta} kg</span>
                </div>
              </div>

              {result.disposal_advice && (
                <div className="mt-4 p-4 bg-secondary/5 border-l-4 border-secondary rounded-r-lg">
                  <p className="text-xs font-bold uppercase tracking-widest text-secondary mb-1">Disposal Advice</p>
                  <p className="text-sm text-on-surface leading-relaxed">{result.disposal_advice}</p>
                </div>
              )}

              <p className="mt-4 text-xs text-on-surface-variant leading-relaxed">Zero-shot classification has no committed representative real-image benchmark in this repository. Condition is a global-image heuristic, and the CO₂ value is a device-profile planning estimate rather than a measured recycling outcome.</p>

              <div className="mt-4 pt-4 border-t border-outline-variant/20 flex items-center justify-between text-xs text-outline">
                <span>Processing: {result.processing_time}s</span>
                <span>ID: {result.analysis_id?.slice(0, 8)}</span>
              </div>
            </motion.div>
          )}

          <div className="bg-surface-container-low p-6 rounded-xl hover-lift card-shadow">
            <h3 className="text-lg font-bold text-on-surface mb-4">Supported Devices</h3>
            <div className="flex flex-wrap gap-2">
              {['Motherboard', 'Hard Disk / SSD', 'Monitor', 'Mouse', 'Keyboard', 'Smartphone', 'Computer', 'Printer', 'Projector', 'Router / Switch', 'Air Conditioner', 'Microwave', 'Television', 'Camera', 'Smartwatch', 'Laptop', 'Battery', 'Washing Machine', 'Refrigerator', 'Remote Control'].map((cls) => (
                <span key={cls} className="bg-surface-container-highest px-3 py-1.5 rounded-full text-sm text-on-surface hover:bg-primary hover:text-on-primary transition-all duration-300 cursor-default hover:scale-105 transform">
                  {cls}
                </span>
              ))}
            </div>
            <p className="text-xs text-outline mt-3">20 canonical categories scored by the selected pre-trained SigLIP 2 or CLIP preset; aliases do not add output classes.</p>
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
                <p className="text-sm text-on-surface-variant">Get device details, CO₂ impact, and disposal recommendation</p>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
    </AnimatedPage>
  )
}

export default Scanner
