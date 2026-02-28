import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import {
  UploadCloud, Activity, Brain, Database, FileSpreadsheet,
  CheckCircle2, Box, Sparkles, ChevronRight, BarChart3, Calculator, Eraser, LineChart, Scissors, Trash2
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const API_BASE = window.location.hostname === 'localhost' && window.location.port === '3000' ? 'http://localhost:8000' : '';

function App() {
  const [file, setFile] = useState(null);
  const [fileId, setFileId] = useState(null);

  // Workflow States
  const [currentStep, setCurrentStep] = useState(null);
  // steps: null -> 'cleaning' -> 'eda' -> 'visualization' -> 'training'

  // Results State
  const [cleaningRes, setCleaningRes] = useState(null);
  const [eda, setEda] = useState(null);
  const [visualizationRes, setVisualizationRes] = useState(null);
  const [droppedCols, setDroppedCols] = useState([]);

  // Visualization Form States
  const [customPlotType, setCustomPlotType] = useState('hist');
  const [customCol1, setCustomCol1] = useState('');
  const [customCol2, setCustomCol2] = useState('');
  const [customPlotUrl, setCustomPlotUrl] = useState(null);
  const [customPlotLoading, setCustomPlotLoading] = useState(false);

  // Form States
  const [featureToDrop, setFeatureToDrop] = useState('');

  const [columnsList, setColumnsList] = useState([]);
  const [previewRows, setPreviewRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);

  const columns = useMemo(() => {
    if (!eda) return [];
    return Object.keys(eda.dtypes || {});
  }, [eda]);

  const activeColumns = columnsList.length ? columnsList : columns;

  useEffect(() => {
    if (!fileId) return;
    async function fetchCols() {
      try {
        setLoading(true);
        const res = await axios.get(`${API_BASE}/columns/${fileId}`);
        setColumnsList(res.data.columns || []);
        setPreviewRows(res.data.preview || []);
      } catch (e) {
        console.error('fetch columns failed', e);
      } finally {
        setLoading(false);
      }
    }
    fetchCols();
  }, [fileId]);

  async function upload() {
    if (!file) return;
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append('file', file);
      const res = await axios.post(`${API_BASE}/upload`, fd);
      setFileId(res.data.file_id);

      // Reset flow
      setCurrentStep(null);
      setCleaningRes(null);
      setEda(null);
      setVisualizationRes(null);
      setCustomPlotUrl(null);
      setDroppedCols([]);
    } catch (e) {
      console.error('Upload failed:', e);
      alert('Upload failed. Is the backend server running?');
    } finally {
      setUploading(false);
    }
  }

  // Data Cleaning via Backend Endpoint
  async function runCleaning() {
    setLoading(true);
    try {
      const res = await axios.post(`${API_BASE}/clean/${fileId}`);
      setCleaningRes({
        status: res.data.status,
        message: res.data.message,
        rowsAfter: res.data.rowsAfter,
        downloadUrl: `${API_BASE}/download/${fileId}`
      });
      setCurrentStep('eda_prompt');

      // refresh columns preview after cleaning changes the rows
      const colRes = await axios.get(`${API_BASE}/columns/${fileId}`);
      setColumnsList(colRes.data.columns || []);
      setPreviewRows(colRes.data.preview || []);
    } catch (e) {
      console.error(e);
      alert('Cleaning failed.');
    } finally {
      setLoading(false);
    }
  }

  async function getEda() {
    setLoading(true);
    try {
      setCurrentStep('eda');
      const res = await axios.get(`${API_BASE}/eda/${fileId}`);
      setEda(res.data);
      setCurrentStep('visualization_prompt');
    } catch (e) {
      console.error('EDA failed:', e);
    } finally {
      setLoading(false);
    }
  }

  // Visualization via Backend Endpoint
  async function runVisualization() {
    setLoading(true);
    try {
      const res = await axios.post(`${API_BASE}/visualize/${fileId}`);
      setVisualizationRes(res.data.plots || []);
      setCurrentStep('refinement');
      if (activeColumns.length > 0) {
        setCustomCol1(activeColumns[0]);
        if (activeColumns.length > 1) setCustomCol2(activeColumns[1]);
      }
    } catch (e) {
      console.error(e);
      alert('Visualization failed.');
    } finally {
      setLoading(false);
    }
  }

  async function generateCustomPlot() {
    if (!customCol1) return;
    setCustomPlotLoading(true);
    try {
      const fd = new FormData();
      fd.append('plot_type', customPlotType);
      fd.append('col1', customCol1);
      if (customPlotType === 'scatter' && customCol2) {
        fd.append('col2', customCol2);
      }
      const res = await axios.post(`${API_BASE}/visualize-custom/${fileId}`, fd);
      setCustomPlotUrl(res.data.plot);
    } catch (e) {
      console.error(e);
      alert('Failed to generate custom plot. Ensure the column type matches the plot type.');
    } finally {
      setCustomPlotLoading(false);
    }
  }

  async function handleDropFeature() {
    if (!featureToDrop) return;
    setLoading(true);
    try {
      const fd = new FormData();
      fd.append('columns', featureToDrop);
      const res = await axios.post(`${API_BASE}/drop-columns/${fileId}`, fd);

      setDroppedCols([...droppedCols, featureToDrop]);
      setFeatureToDrop('');

      // Refresh columns
      const colRes = await axios.get(`${API_BASE}/columns/${fileId}`);
      setColumnsList(colRes.data.columns || []);
      setPreviewRows(colRes.data.preview || []);

    } catch (e) {
      console.error(e);
      alert('Failed to drop feature.');
    } finally {
      setLoading(false);
    }
  }

  const handleDragOver = (e) => e.preventDefault();
  const handleDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  // Step Workflow Card Component
  const WorkflowPrompt = ({ icon: Icon, title, description, actionLabel, onAction, disableAction }) => (
    <motion.div
      initial={{ opacity: 0, scale: 0.95, y: 10 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      className="glass-panel p-6 border-indigo-500/30 shadow-indigo-500/10 mb-6 bg-indigo-900/10"
    >
      <div className="flex items-start justify-between">
        <div className="flex gap-4">
          <div className="p-3 bg-indigo-500/20 rounded-xl text-indigo-400">
            <Icon className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-xl font-semibold text-white mb-1">{title}</h3>
            <p className="text-slate-400 max-w-md text-sm">{description}</p>
          </div>
        </div>
        <button
          onClick={onAction}
          disabled={disableAction || loading}
          className="btn-primary group flex items-center gap-2"
        >
          {loading ? 'Processing...' : actionLabel}
          {!loading && <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />}
        </button>
      </div>
    </motion.div>
  );

  return (
    <div className="min-h-screen relative overflow-hidden text-slate-200">
      <div className="absolute top-0 -left-4 w-96 h-96 bg-indigo-500 rounded-full mix-blend-multiply filter blur-[128px] opacity-20 animate-pulse"></div>
      <div className="absolute top-0 -right-4 w-96 h-96 bg-teal-500 rounded-full mix-blend-multiply filter blur-[128px] opacity-20 animate-pulse" style={{ animationDelay: '2s' }}></div>

      <div className="relative z-10 max-w-5xl mx-auto px-6 py-8">

        <header className="flex items-center justify-between mb-12 animate-slide-up">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-indigo-500 to-teal-400 flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <Sparkles className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold heading-gradient">Nexus ML</h1>
              <p className="text-sm text-slate-400 font-medium">Step-by-Step Intelligence Pipeline</p>
            </div>
          </div>
        </header>

        <main className="space-y-8">

          {/* STEP 1: Upload */}
          <section className="glass-panel p-6 animate-slide-up">
            <div className="flex items-center justify-between mb-6 border-b border-slate-700/50 pb-4">
              <div className="flex items-center gap-3">
                <Database className="w-5 h-5 text-indigo-400" />
                <h2 className="text-lg font-semibold text-white">1. Dataset Injection</h2>
              </div>
              {fileId && <span className="text-emerald-400 text-xs font-semibold px-2 py-1 bg-emerald-500/10 rounded-full">Completed</span>}
            </div>

            {!fileId ? (
              <div
                className={`border-2 border-dashed rounded-2xl p-10 text-center transition-all duration-300 ${file ? 'border-indigo-500 bg-indigo-500/5' : 'border-slate-700 hover:border-indigo-400 hover:bg-slate-800/50'}`}
                onDragOver={handleDragOver}
                onDrop={handleDrop}
              >
                <div className="bg-slate-800 p-4 rounded-full w-max mx-auto mb-4 shadow-inner">
                  <UploadCloud className={`w-8 h-8 ${file ? 'text-indigo-400' : 'text-slate-400'}`} />
                </div>
                <p className="text-base text-white mb-2 font-medium">
                  {file ? file.name : "Drag & drop your CSV or Excel file here"}
                </p>
                <input type="file" id="file-upload" className="hidden" onChange={e => setFile(e.target.files[0])} />
                <div className="flex items-center justify-center gap-4 mt-6">
                  <label htmlFor="file-upload" className="btn-secondary cursor-pointer">Browse Files</label>
                  <button onClick={upload} disabled={!file || uploading} className="btn-primary flex items-center gap-2">
                    {uploading ? 'Uploading...' : 'Upload & Start'}
                  </button>
                </div>
              </div>
            ) : (
              <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                  <div>
                    <span className="text-sm text-slate-300">Active FileID:</span>
                    <span className="ml-2 font-mono text-xs text-indigo-300 bg-indigo-900/50 px-2 py-1 rounded">{fileId}</span>
                  </div>
                </div>
                <button onClick={() => { setFileId(null); setFile(null); setCurrentStep(null); }} className="text-xs text-slate-400 hover:text-white underline underline-offset-2">Reset</button>
              </div>
            )}
          </section>

          <AnimatePresence>
            {/* STEP 2: Data Cleaning */}
            {fileId && !cleaningRes && currentStep !== 'eda_prompt' && currentStep !== 'visualization_prompt' && currentStep !== 'training_prompt' && (
              <WorkflowPrompt
                icon={Eraser}
                title="2. Prepare & Clean Data"
                description="Before analyzing, we should standardize formats, handle missing values, and remove duplicates to ensure high model quality."
                actionLabel="Execute Cleaning"
                onAction={runCleaning}
              />
            )}

            {cleaningRes && (
              <motion.section initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} className="glass-panel p-6 border-l-4 border-emerald-500 overflow-hidden">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Eraser className="w-5 h-5 text-emerald-400" />
                    <h2 className="text-lg font-semibold text-white">2. Cleaning Complete</h2>
                  </div>
                  <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                </div>
                <div className="mt-4 flex flex-col sm:flex-row items-center justify-between bg-emerald-900/20 p-4 rounded-lg border border-emerald-500/20">
                  <p className="text-sm text-emerald-100 mb-4 sm:mb-0">{cleaningRes.message}</p>
                  <a href={cleaningRes.downloadUrl} className="btn-secondary whitespace-nowrap !text-emerald-400 !border-emerald-500/50 hover:bg-emerald-500/10">Download Cleaned Dataset</a>
                </div>

                {previewRows && previewRows.length > 0 && (
                  <div className="mt-6 border border-slate-700/50 rounded-xl overflow-hidden bg-slate-900/50">
                    <div className="bg-slate-800/80 px-4 py-2 border-b border-slate-700/50">
                      <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Data Preview (Top 5 Rows)</h4>
                    </div>
                    <div className="overflow-x-auto custom-scrollbar">
                      <table className="w-full text-left text-xs text-slate-300">
                        <thead className="bg-slate-800/40 text-slate-400">
                          <tr>
                            {activeColumns.map(col => (
                              <th key={col} className="px-4 py-3 font-medium whitespace-nowrap">{col}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/50">
                          {previewRows.map((row, i) => (
                            <tr key={i} className="hover:bg-slate-800/30 transition-colors">
                              {activeColumns.map(col => (
                                <td key={col} className="px-4 py-2 whitespace-nowrap truncate max-w-[150px]">{String(row[col] ?? '')}</td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </motion.section>
            )}

            {/* STEP 3: EDA */}
            {currentStep === 'eda_prompt' && (
              <WorkflowPrompt
                icon={FileSpreadsheet}
                title="3. Exploratory Data Analysis"
                description="Now that the data is clean, let's scan the feature architecture to understand the distributions, correlations, and schema."
                actionLabel="Run EDA Engine"
                onAction={getEda}
              />
            )}

            {eda && (
              <motion.section initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="glass-panel p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <FileSpreadsheet className="w-5 h-5 text-blue-400" />
                    <h2 className="text-lg font-semibold text-white">3. EDA Registry</h2>
                  </div>
                  <CheckCircle2 className="w-5 h-5 text-blue-400" />
                </div>

                <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
                  {activeColumns.slice(0, 8).map(c => (
                    <div key={c} className="bg-slate-800/80 px-3 py-2 rounded-lg border border-slate-700/50">
                      <span className="text-xs font-medium text-slate-200 truncate block">{c}</span>
                      <span className="text-[10px] text-blue-400 mt-1 block">{eda.dtypes?.[c] || 'Unknown'}</span>
                    </div>
                  ))}
                  {activeColumns.length > 8 && <div className="text-xs text-slate-400 flex items-center justify-center p-2">+ {activeColumns.length - 8} more columns</div>}
                </div>
              </motion.section>
            )}

            {/* STEP 4: Visualization */}
            {currentStep === 'visualization_prompt' && (
              <WorkflowPrompt
                icon={LineChart}
                title="4. Visual Patterns"
                description="Do you want to generate visual charts and graphs (Histograms, Box plots, Scatter plots, Heatmap) for the numeric features before moving to training?"
                actionLabel="Generate Visuals"
                onAction={runVisualization}
              />
            )}

            {visualizationRes && (
              <motion.section initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="glass-panel p-6 mb-6">
                <div className="flex items-center justify-between mb-6 border-b border-slate-700/50 pb-4">
                  <div className="flex items-center gap-3">
                    <LineChart className="w-5 h-5 text-pink-400" />
                    <h2 className="text-xl font-semibold text-white">4. Visual Patterns</h2>
                  </div>
                  <CheckCircle2 className="w-5 h-5 text-pink-400" />
                </div>

                {/* Custom Plot Builder */}
                <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-5 mb-8">
                  <h3 className="text-sm font-semibold text-slate-300 mb-4 flex items-center gap-2">
                    <Activity className="w-4 h-4 text-pink-400" /> Custom Chart Builder
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
                    <div className="md:col-span-1">
                      <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Plot Type</label>
                      <select className="select-field" value={customPlotType} onChange={e => setCustomPlotType(e.target.value)}>
                        <option value="hist">Histogram</option>
                        <option value="kde">KDE Plot</option>
                        <option value="cdf">CDF Plot</option>
                        <option value="box">Box Plot</option>
                        <option value="count">Count Plot (Categorical)</option>
                        <option value="scatter">Scatter Plot</option>
                      </select>
                    </div>
                    <div className="md:col-span-1">
                      <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Primary Feature (X)</label>
                      <select className="select-field" value={customCol1} onChange={e => setCustomCol1(e.target.value)}>
                        {activeColumns.map(c => <option key={c} value={c}>{c}</option>)}
                      </select>
                    </div>
                    {customPlotType === 'scatter' && (
                      <div className="md:col-span-1 animate-fade-in">
                        <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Secondary Feature (Y)</label>
                        <select className="select-field" value={customCol2} onChange={e => setCustomCol2(e.target.value)}>
                          {activeColumns.map(c => <option key={c} value={c}>{c}</option>)}
                        </select>
                      </div>
                    )}
                    <div className="md:col-span-1 flex items-end">
                      <button
                        onClick={generateCustomPlot}
                        disabled={customPlotLoading}
                        className="btn-secondary w-full hover:bg-pink-500/20 hover:border-pink-500/50 hover:text-pink-300 flex items-center justify-center gap-2"
                      >
                        {customPlotLoading ? 'Rendering...' : 'Plot Graph'}
                      </button>
                    </div>
                  </div>

                  {customPlotUrl && (
                    <div className="mt-6 bg-white rounded-xl overflow-hidden border border-slate-700 shadow flex items-center justify-center p-4 min-h-[300px] animate-fade-in">
                      <img src={customPlotUrl} alt="Custom Plot" className="max-w-full max-h-[500px] object-contain" />
                    </div>
                  )}
                </div>

                <h3 className="text-sm font-semibold text-slate-300 mb-4 flex items-center gap-2">
                  <Box className="w-4 h-4 text-pink-400" /> Auto-Generated Overview
                </h3>
                {visualizationRes.length > 0 ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {visualizationRes.map((url, idx) => (
                      <div key={idx} className="bg-white rounded-xl overflow-hidden border border-slate-700 shadow flex items-center justify-center p-2">
                        <img src={url} alt={`Visualization ${idx}`} className="max-w-full h-auto object-contain loading-lazy" />
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-slate-400 text-center py-4 bg-slate-900 rounded-lg">No numeric charts could be generated.</p>
                )}
              </motion.section>
            )}

            {/* STEP 5: Feature Trimming */}
            {(currentStep === 'refinement') && (
              <motion.section initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="glass-panel p-6 border-l-4 border-amber-500/50 mb-6">
                <div className="flex items-center gap-3 mb-4">
                  <Scissors className="w-5 h-5 text-amber-400" />
                  <div>
                    <h2 className="text-lg font-semibold text-white">5. Feature Refinement</h2>
                    <p className="text-xs text-slate-400">Notice an outlier or irrelevant feature? Drop it here and download your final dataset.</p>
                  </div>
                </div>

                <div className="flex flex-col md:flex-row gap-4 items-end bg-slate-900/40 p-4 rounded-xl border border-slate-700/50">
                  <div className="w-full md:flex-1">
                    <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Select column to drop</label>
                    <select className="select-field" value={featureToDrop} onChange={e => setFeatureToDrop(e.target.value)}>
                      <option value="">-- View Columns --</option>
                      {activeColumns.map(c => <option key={c} value={c}>{c}</option>)}
                    </select>
                  </div>
                  <button onClick={handleDropFeature} disabled={!featureToDrop || loading} className="btn-secondary whitespace-nowrap !text-amber-400 !border-amber-500/50 hover:bg-amber-500/10 flex items-center gap-2">
                    <Trash2 className="w-4 h-4" /> Drop Column
                  </button>
                </div>

                {droppedCols.length > 0 && (
                  <div className="mt-6 flex flex-col sm:flex-row items-center justify-between bg-amber-900/10 p-4 rounded-lg border border-amber-500/20">
                    <div className="flex gap-2 flex-wrap items-center mb-4 sm:mb-0">
                      <span className="text-xs text-slate-400 mr-2">Dropped features:</span>
                      {droppedCols.map(c => (
                        <span key={c} className="text-xs px-2 py-1 bg-amber-500/10 text-amber-300 rounded border border-amber-500/20 line-through">
                          {c}
                        </span>
                      ))}
                    </div>
                    <a href={`${API_BASE}/download/${fileId}`} className="btn-secondary whitespace-nowrap !text-amber-400 !border-amber-500/50 hover:bg-amber-500/10">
                      Download Truncated Dataset
                    </a>
                  </div>
                )}
              </motion.section>
            )}

          </AnimatePresence>

        </main>
      </div>
    </div>
  );
}

export default App;
