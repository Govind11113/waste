import { useState, useRef } from 'react'

function Scanner() {
  const [file, setFile] = useState(null)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const fileInputRef = useRef(null)

  const handleFileSelect = (e) => {
    const selectedFile = e.target.files[0]
    if (selectedFile) {
      setFile(selectedFile)
      setResult(null)
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    const droppedFile = e.dataTransfer.files[0]
    if (droppedFile && droppedFile.type.startsWith('image/')) {
      setFile(droppedFile)
      setResult(null)
    }
  }

  const handleAnalyze = async () => {
    if (!file) return

    setLoading(true)
    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await fetch('/api/v1/classifier/scan', {
        method: 'POST',
        body: formData
      })
      const data = await response.json()
      setResult(data)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="pt-32 pb-20 px-8 max-w-7xl mx-auto">
      <header className="mb-12">
        <h1 className="text-5xl font-extrabold text-on-surface tracking-tight mb-4">E-Waste Classifier</h1>
        <p className="text-xl text-on-surface-variant max-w-2xl">Upload device images for instant classification using EfficientNetV2-S. Identify e-waste categories with confidence scores and environmental impact metrics.</p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <section>
          <div
            onClick={() => fileInputRef.current?.click()}
            onDrop={handleDrop}
            onDragOver={(e) => e.preventDefault()}
            className="bg-surface-container-lowest border-2 border-dashed border-outline-variant rounded-xl p-12 text-center cursor-pointer hover:border-secondary transition-colors"
          >
            <span className="material-symbols-outlined text-6xl text-outline mb-4">cloud_upload</span>
            <p className="text-lg font-semibold text-on-surface mb-2">Drop image here or click to upload</p>
            <p className="text-sm text-outline">Supports JPG, PNG up to 10MB</p>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={handleFileSelect}
              className="hidden"
            />
          </div>

          {file && (
            <div className="mt-4 p-4 bg-surface-container rounded-xl">
              <p className="text-sm text-on-surface font-medium">Selected: {file.name}</p>
              <button
                onClick={handleAnalyze}
                disabled={loading}
                className="mt-3 w-full bg-primary text-on-primary py-3 rounded-lg font-bold hover:opacity-90 transition-all disabled:opacity-50"
              >
                {loading ? 'Analyzing...' : 'Analyze Image'}
              </button>
            </div>
          )}

          {result && (
            <div className="mt-6 bg-surface-container-lowest p-6 rounded-xl">
              <h3 className="text-xl font-bold text-on-surface mb-4">Analysis Results</h3>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-on-surface-variant">Entity:</span>
                  <span className="font-semibold text-on-surface">{result.entity}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-on-surface-variant">Category:</span>
                  <span className="font-semibold text-on-surface">{result.group}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-on-surface-variant">Status:</span>
                  <span className={`font-semibold ${result.waste_status === 'E-Waste' ? 'text-error' : 'text-secondary'}`}>
                    {result.waste_status}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-on-surface-variant">Confidence:</span>
                  <span className="font-semibold text-on-surface">{(result.confidence * 100).toFixed(1)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-on-surface-variant">CO2 Delta:</span>
                  <span className="font-semibold text-primary">{result.co2_delta} kg</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-on-surface-variant">Condition:</span>
                  <span className="font-semibold text-on-surface capitalize">{result.condition}</span>
                </div>
              </div>
            </div>
          )}
        </section>

        <section className="space-y-6">
          <div className="bg-surface-container-low p-6 rounded-xl">
            <h3 className="text-lg font-bold text-on-surface mb-4">Supported Device Classes</h3>
            <div className="flex flex-wrap gap-2">
              {['Motherboard', 'Hard Disk / SSD', 'Monitor', 'Mouse', 'Keyboard', 'Smartphone', 'Computer', 'Printer', 'Projector', 'Router / Switch'].map((cls) => (
                <span key={cls} className="bg-surface-container-highest px-3 py-1 rounded-full text-sm text-on-surface">
                  {cls}
                </span>
              ))}
            </div>
          </div>

          <div className="bg-surface-container-low p-6 rounded-xl">
            <h3 className="text-lg font-bold text-on-surface mb-4">Classification Rationale</h3>
            <p className="text-sm text-on-surface-variant leading-relaxed">
              Our ResNet50 model has been fine-tuned on an NVIDIA H200 GPU using high-performance datasets. It analyzes visual features to classify items into specific waste categories with high accuracy.
            </p>
          </div>

          <div className="bg-primary/5 p-6 rounded-xl border-l-4 border-primary">
            <h4 className="font-bold text-on-surface mb-2">Sustainability Loop</h4>
            <p className="text-sm text-on-surface-variant">Accurate classification enables optimized recycling pathways, maximizing material recovery and minimizing environmental impact.</p>
          </div>
        </section>
      </div>
    </div>
  )
}

export default Scanner
