import React, { useState, useCallback, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import axios from 'axios';
import { 
  Upload, 
  FileText, 
  Trash2, 
  Download, 
  Settings,
  BarChart3,
  Table,
  CheckCircle,
  Loader2,
  Github,
  Linkedin,
  Globe,
  Heart,
  Coffee,
  ChevronDown,
  ChevronUp,
  ArrowRight,
  AlertTriangle,
  FileCheck,
  Activity
} from 'lucide-react';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const App = () => {
  // State management
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [originalData, setOriginalData] = useState(null);
  const [cleanedData, setCleanedData] = useState(null);
  const [statistics, setStatistics] = useState(null);
  const [cleanedStatistics, setCleanedStatistics] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isCleaning, setIsCleaning] = useState(false);
  const [cleaningComplete, setCleaningComplete] = useState(false);
  const [showOriginalExpanded, setShowOriginalExpanded] = useState(false);
  const [showCleanedExpanded, setShowCleanedExpanded] = useState(false);
  const [downloadInProgress, setDownloadInProgress] = useState({});
  const [cleaningOptions, setCleaningOptions] = useState({
    remove_duplicates: false,
    handle_missing: 'none',
    fill_value: '',
    column_renames: {},
    find_replace: {},
    trim_whitespace: false,
    data_type_conversions: {},
    merge_files: []
  });

  // File upload with drag and drop
  const onDrop = useCallback(async (acceptedFiles) => {
    setIsUploading(true);
    
    for (const file of acceptedFiles) {
      try {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await axios.post(`${API}/upload`, formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        });
        
        const newFile = response.data;
        setUploadedFiles(prev => [...prev, newFile]);
        
        // If this is the first file, select it automatically
        if (uploadedFiles.length === 0) {
          setSelectedFile(newFile);
          setOriginalData(newFile.preview_data);
          setStatistics(newFile.statistics);
        }
      } catch (error) {
        console.error('Upload failed:', error);
        const errorMessage = error.response?.data?.detail || error.message || 'Upload failed';
        alert(`Upload failed: ${errorMessage}`);
      }
    }
    
    setIsUploading(false);
  }, [uploadedFiles.length]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/json': ['.json']
    },
    multiple: true
  });

  // Enhanced clean data function with better animations
  const cleanData = async () => {
    if (!selectedFile) return;
    
    setIsCleaning(true);
    setCleaningComplete(false);
    
    try {
      const formData = new FormData();
      formData.append('file_id', selectedFile.file_info.id);
      formData.append('options', JSON.stringify(cleaningOptions));
      
      const response = await axios.post(`${API}/clean`, formData);
      const result = response.data;
      
      setCleanedData(result.preview_data);
      setCleanedStatistics(result.statistics);
      setCleaningComplete(true);
      
      // Show success message with animation
      setTimeout(() => {
        setCleaningComplete(false);
      }, 3000);
      
    } catch (error) {
      console.error('Cleaning failed:', error);
      const errorMessage = error.response?.data?.detail || error.message || 'Cleaning operation failed';
      alert(`Cleaning failed: ${errorMessage}`);
    }
    
    setIsCleaning(false);
  };

  // Enhanced download file function with loading states
  const downloadFile = async (fileId, format = 'csv', isOriginal = false) => {
    const downloadKey = `${fileId}-${format}-${isOriginal}`;
    
    try {
      setDownloadInProgress(prev => ({ ...prev, [downloadKey]: true }));
      
      const response = await axios.get(`${API}/download/${fileId}?format=${format}`, {
        responseType: 'blob'
      });
      
      const blob = new Blob([response.data]);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${isOriginal ? 'original' : 'cleaned'}_data.${format}`;
      
      // Improved download UX
      document.body.appendChild(a);
      a.click();
      
      // Cleanup
      setTimeout(() => {
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      }, 100);
      
    } catch (error) {
      console.error('Download failed:', error);
      const errorMessage = error.response?.data?.detail || error.message || 'Download failed';
      alert(`Download failed: ${errorMessage}`);
    } finally {
      setDownloadInProgress(prev => ({ ...prev, [downloadKey]: false }));
    }
  };

  // Delete file function
  const deleteFile = async (fileId) => {
    try {
      await axios.delete(`${API}/file/${fileId}`);
      setUploadedFiles(prev => prev.filter(f => f.file_info.id !== fileId));
      if (selectedFile && selectedFile.file_info.id === fileId) {
        setSelectedFile(null);
        setOriginalData(null);
        setCleanedData(null);
        setStatistics(null);
        setCleanedStatistics(null);
        setCleaningComplete(false);
      }
    } catch (error) {
      console.error('Delete failed:', error);
      alert('Delete operation failed');
    }
  };

  // Handle cleaning option changes
  const updateCleaningOption = (key, value) => {
    setCleaningOptions(prev => ({
      ...prev,
      [key]: value
    }));
  };

  const updateColumnRename = (oldName, newName) => {
    setCleaningOptions(prev => ({
      ...prev,
      column_renames: {
        ...prev.column_renames,
        [oldName]: newName
      }
    }));
  };

  // Utility functions
  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatNumber = (num) => {
    if (typeof num !== 'number' || isNaN(num)) return 'N/A';
    return Number.isInteger(num) ? num.toString() : num.toFixed(2);
  };

  // Enhanced data table renderer
  const renderDataTable = (data, isExpanded, toggleExpanded, tableClass = '') => {
    if (!data || data.length === 0) {
      return (
        <div className="table-container">
          <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
            <AlertTriangle size={32} style={{ marginBottom: '1rem', opacity: 0.5 }} />
            <p>No data available</p>
          </div>
        </div>
      );
    }
    
    const displayData = isExpanded ? data : data.slice(0, 5);
    const hasMoreRows = data.length > 5;

    return (
      <div className="table-container">
        <div className={`${!isExpanded && hasMoreRows ? 'table-collapsed' : ''}`}>
          <table className={`data-table ${tableClass}`}>
            <thead>
              <tr>
                {Object.keys(data[0] || {}).map((column) => (
                  <th key={column} title={column}>
                    <span className="text-truncate">{column}</span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {displayData.map((row, index) => (
                <tr key={index}>
                  {Object.values(row).map((value, cellIndex) => (
                    <td key={cellIndex} title={value !== null && value !== undefined ? String(value) : 'N/A'}>
                      <span className="text-truncate">
                        {value !== null && value !== undefined ? String(value) : 'N/A'}
                      </span>
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        
        {hasMoreRows && (
          <div className="table-controls">
            <button
              onClick={toggleExpanded}
              className="btn btn-secondary btn-sm"
              aria-label={isExpanded ? 'Show less rows' : `Show all ${data.length} rows`}
            >
              {isExpanded ? (
                <>
                  <ChevronUp className="icon" />
                  Show Less
                </>
              ) : (
                <>
                  <ChevronDown className="icon" />
                  View More ({data.length - 5} more rows)
                </>
              )}
            </button>
          </div>
        )}
      </div>
    );
  };

  // Enhanced download button renderer
  const renderDownloadButton = (fileId, format, label, className = 'btn-secondary') => {
    const downloadKey = `${fileId}-${format}-false`;
    const isLoading = downloadInProgress[downloadKey];
    
    return (
      <button
        onClick={() => downloadFile(fileId, format)}
        disabled={isLoading}
        className={`btn ${className} btn-sm`}
        aria-label={`Download as ${format.toUpperCase()}`}
      >
        {isLoading ? (
          <>
            <Loader2 className="icon spinner" />
            <span className="sr-only">Downloading...</span>
          </>
        ) : (
          <>
            <Download className="icon" />
            {label}
          </>
        )}
      </button>
    );
  };

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <h1 className="app-title">Data Cleaner</h1>
        <p className="app-subtitle">Professional data cleaning and processing tool</p>
      </header>

      {/* Main Content */}
      <main style={{ maxWidth: '1200px', margin: '0 auto', padding: '0 1rem 5rem 1rem' }}>
        
        {/* File Upload Card */}
        <div className="card">
          <div className="card-header">
            <Upload className="card-header-icon" />
            <h2 className="card-title">File Upload</h2>
          </div>
          
          <div
            {...getRootProps()}
            className={`upload-zone ${isDragActive ? 'drag-active' : ''} ${isUploading ? 'uploading' : ''}`}
            role="button"
            tabIndex={0}
            aria-label="File upload area"
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
              }
            }}
          >
            <input {...getInputProps()} />
            {isUploading ? (
              <div className="loading-container">
                <div className="loading-container">
                  <div className="pulse-dot"></div>
                  <div className="pulse-dot"></div>
                  <div className="pulse-dot"></div>
                </div>
                <span className="upload-text">Uploading files...</span>
              </div>
            ) : (
              <div>
                <Upload className="upload-icon" />
                <p className="upload-text">
                  {isDragActive ? 'Drop files here...' : 'Drag & drop files here, or click to select'}
                </p>
                <p className="upload-subtext">
                  Supports CSV, XLSX, and JSON files up to 10MB each
                </p>
              </div>
            )}
          </div>

          {/* Uploaded Files */}
          {uploadedFiles.length > 0 && (
            <div className="file-list">
              <h3 className="file-list-title">Uploaded Files</h3>
              <div role="list" aria-label="Uploaded files">
                {uploadedFiles.map((file, index) => (
                  <div
                    key={index}
                    className={`file-item ${selectedFile?.file_info.id === file.file_info.id ? 'selected' : ''}`}
                    onClick={() => {
                      setSelectedFile(file);
                      setOriginalData(file.preview_data);
                      setStatistics(file.statistics);
                      setCleanedData(null);
                      setCleanedStatistics(null);
                      setShowOriginalExpanded(false);
                      setShowCleanedExpanded(false);
                      setCleaningComplete(false);
                    }}
                    role="listitem button"
                    tabIndex={0}
                    aria-label={`Select file ${file.file_info.filename}`}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        // Trigger click behavior
                      }
                    }}
                  >
                    <div className="file-info">
                      <FileText className="file-icon" />
                      <div className="file-details">
                        <h4>{file.file_info.filename}</h4>
                        <p>{file.file_info.file_type.toUpperCase()} • {formatFileSize(file.file_info.size)}</p>
                      </div>
                    </div>
                    <div className="file-actions">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          downloadFile(file.file_info.id, file.file_info.file_type, true);
                        }}
                        className="btn-icon"
                        title="Download Original"
                        aria-label={`Download original ${file.file_info.filename}`}
                      >
                        <Download className="icon" />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteFile(file.file_info.id);
                        }}
                        className="btn-icon"
                        title="Delete File"
                        aria-label={`Delete ${file.file_info.filename}`}
                      >
                        <Trash2 className="icon" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {selectedFile && (
          <>
            {/* Data Cleaning Options Card */}
            <div className="card">
              <div className="card-header">
                <Settings className="card-header-icon" />
                <h2 className="card-title">Data Cleaning Options</h2>
              </div>
              
              <div className="grid grid-cols-3">
                {/* Remove Duplicates */}
                <div className="form-group">
                  <div className="form-checkbox">
                    <input
                      type="checkbox"
                      id="remove-duplicates"
                      checked={cleaningOptions.remove_duplicates}
                      onChange={(e) => updateCleaningOption('remove_duplicates', e.target.checked)}
                      aria-describedby="remove-duplicates-desc"
                    />
                    <label htmlFor="remove-duplicates">Remove Duplicates</label>
                  </div>
                  <p id="remove-duplicates-desc" className="visually-hidden">
                    Remove duplicate rows from the dataset
                  </p>
                </div>

                {/* Handle Missing Values */}
                <div className="form-group">
                  <label htmlFor="missing-values" className="form-label">Handle Missing Values</label>
                  <select
                    id="missing-values"
                    value={cleaningOptions.handle_missing}
                    onChange={(e) => updateCleaningOption('handle_missing', e.target.value)}
                    className="form-select"
                    aria-describedby="missing-values-desc"
                  >
                    <option value="none">Keep as is</option>
                    <option value="drop">Drop rows</option>
                    <option value="fill">Fill with value</option>
                  </select>
                  <p id="missing-values-desc" className="visually-hidden">
                    Choose how to handle missing or null values
                  </p>
                  {cleaningOptions.handle_missing === 'fill' && (
                    <input
                      type="text"
                      placeholder="Fill value"
                      value={cleaningOptions.fill_value}
                      onChange={(e) => updateCleaningOption('fill_value', e.target.value)}
                      className="form-input mt-2"
                      aria-label="Fill value for missing data"
                    />
                  )}
                </div>

                {/* Trim Whitespace */}
                <div className="form-group">
                  <div className="form-checkbox">
                    <input
                      type="checkbox"
                      id="trim-whitespace"
                      checked={cleaningOptions.trim_whitespace}
                      onChange={(e) => updateCleaningOption('trim_whitespace', e.target.checked)}
                      aria-describedby="trim-whitespace-desc"
                    />
                    <label htmlFor="trim-whitespace">Trim Whitespace</label>
                  </div>
                  <p id="trim-whitespace-desc" className="visually-hidden">
                    Remove leading and trailing whitespace from text fields
                  </p>
                </div>
              </div>

              {/* Column Renaming */}
              {originalData && originalData.length > 0 && (
                <div className="form-group mt-6">
                  <h3 className="form-label text-primary mb-4">Column Renaming</h3>
                  <div className="column-rename-grid">
                    {Object.keys(originalData[0] || {}).map((column, index) => (
                      <div key={index} className="column-rename-item">
                        <span className="form-input text-secondary text-truncate" style={{ flex: '1', background: 'var(--bg-accent)', cursor: 'default', border: 'none' }}>
                          {column}
                        </span>
                        <ArrowRight className="rename-arrow" size={16} />
                        <input
                          type="text"
                          placeholder={`New name for ${column}`}
                          value={cleaningOptions.column_renames[column] || ''}
                          onChange={(e) => updateColumnRename(column, e.target.value)}
                          className="form-input"
                          style={{ flex: '1' }}
                          aria-label={`Rename column ${column}`}
                        />
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Enhanced Clean Data Button */}
              <div className="mt-6">
                <button
                  onClick={cleanData}
                  disabled={isCleaning}
                  className={`btn btn-full btn-lg ${cleaningComplete ? 'btn-success' : 'btn-primary'}`}
                  aria-describedby="clean-button-status"
                >
                  {isCleaning ? (
                    <div className="loading-container">
                      <Loader2 className="icon spinner" />
                      <span>Processing Data...</span>
                    </div>
                  ) : cleaningComplete ? (
                    <div className="success-animation">
                      <CheckCircle className="icon success-checkmark" />
                      <span>Data Cleaned Successfully!</span>
                    </div>
                  ) : (
                    <>
                      <Activity className="icon" />
                      <span>Clean Data</span>
                    </>
                  )}
                </button>
                <p id="clean-button-status" className="visually-hidden">
                  {isCleaning ? 'Cleaning in progress' : cleaningComplete ? 'Cleaning completed successfully' : 'Ready to clean data'}
                </p>
              </div>
            </div>

            {/* Data Statistics Card */}
            {statistics && (
              <div className="card">
                <div className="card-header">
                  <BarChart3 className="card-header-icon" />
                  <h2 className="card-title">Data Statistics</h2>
                </div>
                
                <div className="stats-grid">
                  <div className="stat-card">
                    <p className="stat-label">Total Rows</p>
                    <p className="stat-value">{formatNumber(statistics.rows)}</p>
                  </div>
                  <div className="stat-card">
                    <p className="stat-label">Total Columns</p>
                    <p className="stat-value">{formatNumber(statistics.columns)}</p>
                  </div>
                  <div className="stat-card">
                    <p className="stat-label">Missing Values</p>
                    <p className="stat-value">
                      {formatNumber(Object.values(statistics.missing_values).reduce((a, b) => a + b, 0))}
                    </p>
                  </div>
                  <div className="stat-card">
                    <p className="stat-label">Data Quality</p>
                    <p className="stat-value">
                      {statistics.rows > 0 && statistics.columns > 0 ? 
                        Math.round((1 - Object.values(statistics.missing_values).reduce((a, b) => a + b, 0) / (statistics.rows * statistics.columns)) * 100) : 0}%
                    </p>
                  </div>
                </div>

                {/* Numeric Statistics */}
                {Object.keys(statistics.numeric_stats).length > 0 && (
                  <div>
                    <h3 className="form-label text-primary mb-3">Numeric Column Statistics</h3>
                    <div className="table-container">
                      <table className="data-table">
                        <thead>
                          <tr>
                            <th>Column</th>
                            <th>Minimum</th>
                            <th>Maximum</th>
                            <th>Average</th>
                            <th>Std Dev</th>
                          </tr>
                        </thead>
                        <tbody>
                          {Object.entries(statistics.numeric_stats).map(([col, stats]) => (
                            <tr key={col}>
                              <td className="text-accent font-semibold">{col}</td>
                              <td>{formatNumber(stats.min)}</td>
                              <td>{formatNumber(stats.max)}</td>
                              <td>{formatNumber(stats.mean)}</td>
                              <td>{formatNumber(stats.std)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Original Data Card */}
            {originalData && (
              <div className="card">
                <div className="card-header">
                  <Table className="card-header-icon" />
                  <h2 className="card-title">Original Data Preview</h2>
                </div>
                
                {renderDataTable(
                  originalData, 
                  showOriginalExpanded, 
                  () => setShowOriginalExpanded(!showOriginalExpanded)
                )}
              </div>
            )}

            {/* Cleaned Data Card */}
            {cleanedData && (
              <div className="card">
                <div className="card-header space-between">
                  <div className="card-title-group">
                    <FileCheck className="card-header-icon" style={{ color: 'var(--success-color)' }} />
                    <h2 className="card-title text-success">Cleaned Data Preview</h2>
                  </div>
                  <div className="download-group">
                    {renderDownloadButton(selectedFile.file_info.id, 'csv', 'CSV')}
                    {renderDownloadButton(selectedFile.file_info.id, 'xlsx', 'Excel')}
                    {renderDownloadButton(selectedFile.file_info.id, 'json', 'JSON')}
                  </div>
                </div>
                
                {cleanedStatistics && (
                  <div className="stats-grid">
                    <div className="stat-card success">
                      <p className="stat-label">Cleaned Rows</p>
                      <p className="stat-value">{formatNumber(cleanedStatistics.rows)}</p>
                    </div>
                    <div className="stat-card success">
                      <p className="stat-label">Columns</p>
                      <p className="stat-value">{formatNumber(cleanedStatistics.columns)}</p>
                    </div>
                    <div className="stat-card success">
                      <p className="stat-label">Missing Values</p>
                      <p className="stat-value">
                        {formatNumber(Object.values(cleanedStatistics.missing_values).reduce((a, b) => a + b, 0))}
                      </p>
                    </div>
                    <div className="stat-card success">
                      <p className="stat-label">Data Quality</p>
                      <p className="stat-value">
                        {cleanedStatistics.rows > 0 && cleanedStatistics.columns > 0 ?
                          Math.round((1 - Object.values(cleanedStatistics.missing_values).reduce((a, b) => a + b, 0) / (cleanedStatistics.rows * cleanedStatistics.columns)) * 100) : 0}%
                      </p>
                    </div>
                  </div>
                )}
                
                {renderDataTable(
                  cleanedData, 
                  showCleanedExpanded, 
                  () => setShowCleanedExpanded(!showCleanedExpanded),
                  'cleaned'
                )}
              </div>
            )}
          </>
        )}
      </main>

      {/* Enhanced Footer */}
      <footer className="app-footer">
        <div className="footer-content">
          <p className="footer-text">
            Developed by Sujan Das with <Heart className="heart-icon" /> and way too much <Coffee className="coffee-icon" />
          </p>
          <div className="footer-social" role="group" aria-label="Social media links">
            <a
              href="https://github.com/devsujandas"
              target="_blank"
              rel="noopener noreferrer"
              className="social-link"
              aria-label="GitHub Profile"
            >
              <Github className="social-icon" />
            </a>
            <a
              href="https://in.linkedin.com/in/devsujandas"
              target="_blank"
              rel="noopener noreferrer"
              className="social-link"
              aria-label="LinkedIn Profile"
            >
              <Linkedin className="social-icon" />
            </a>
            <a
              href="https://www.sujandas.info/"
              target="_blank"
              rel="noopener noreferrer"
              className="social-link"
              aria-label="Personal Website"
            >
              <Globe className="social-icon" />
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default App;