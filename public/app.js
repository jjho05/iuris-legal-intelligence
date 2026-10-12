/**
 * IURIS LEGAL INTELLIGENCE — CLIENT ENGINE (app.js)
 * Gestión de subida de PDF/DOCX a Markdown, Grounding Web de leyes, drawer móvil y Gemini 3.8 Flash.
 */

// ==============================================================================
// 1. ESTADO DE LA APLICACIÓN
// ==============================================================================
const state = {
  activeCorpus: 'corporativo',
  uploadedDocName: null,
  uploadedMarkdown: null,
  enableWebSearch: true,
  userApiKey: sessionStorage.getItem('iuris_api_key') || '',
  isProcessing: false,
  apiBase: window.location.origin
};

// ==============================================================================
// 2. REFERENCIAS AL DOM
// ==============================================================================
const dom = {
  // Chat Thread y Composer
  chatThread: document.getElementById('chat-thread'),
  composerForm: document.getElementById('chat-composer-form'),
  composerInput: document.getElementById('composer-input'),
  btnSubmit: document.getElementById('btn-composer-submit'),
  btnAttach: document.getElementById('btn-attach-file'),
  suggestedQueries: document.getElementById('suggested-queries'),
  activeContextLabel: document.getElementById('active-context-label'),
  
  // Controles de Cabecera
  selectFramework: document.getElementById('select-legal-framework'),
  optCustomDoc: document.getElementById('opt-custom-doc'),
  toggleWebSearch: document.getElementById('toggle-web-search'),
  btnTriggerUpload: document.getElementById('btn-trigger-upload'),
  btnOpenKeyModal: document.getElementById('btn-open-key-modal'),
  btnToggleDrawer: document.getElementById('btn-toggle-drawer'),
  
  // Sidebar y Drawer Móvil
  sidebar: document.getElementById('document-sidebar'),
  btnCloseSidebar: document.getElementById('btn-close-sidebar'),
  tabBtnDoc: document.getElementById('tab-btn-document'),
  tabBtnCitations: document.getElementById('tab-btn-citations'),
  panelDoc: document.getElementById('panel-document'),
  panelCitations: document.getElementById('panel-citations'),
  
  // Ingestión de Archivos
  dropzone: document.getElementById('upload-dropzone'),
  fileInput: document.getElementById('file-input'),
  globalFileInput: document.getElementById('global-file-input'),
  docMetaCard: document.getElementById('doc-meta-card'),
  docNameLabel: document.getElementById('doc-name-label'),
  docTypeBadge: document.getElementById('doc-type-badge'),
  docWordsStat: document.getElementById('doc-words-stat'),
  docSectionsStat: document.getElementById('doc-sections-stat'),
  btnCopyMd: document.getElementById('btn-copy-md'),
  btnDownloadMd: document.getElementById('btn-download-md'),
  markdownViewer: document.getElementById('markdown-viewer'),
  citationsList: document.getElementById('citations-list'),
  
  // Modal API Key
  modalKey: document.getElementById('modal-key-config'),
  btnCloseKeyModal: document.getElementById('btn-close-key-modal'),
  inputGeminiKey: document.getElementById('input-gemini-key'),
  btnSaveKey: document.getElementById('btn-save-key'),
  btnResetKey: document.getElementById('btn-reset-key')
};

// ==============================================================================
// 3. INICIALIZACIÓN
// ==============================================================================
async function init() {
  dom.inputGeminiKey.value = state.userApiKey;
  setupEvents();
  await loadCorpusPreview('corporativo');
}

// ==============================================================================
// 4. CONFIGURACIÓN DE EVENTOS
// ==============================================================================
function setupEvents() {
  // Auto-resize de composer
  dom.composerInput.addEventListener('input', () => {
    dom.composerInput.style.height = 'auto';
    dom.composerInput.style.height = Math.min(dom.composerInput.scrollHeight, 120) + 'px';
  });

  // Envío con Enter (Shift+Enter para nueva línea)
  dom.composerInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      dom.composerForm.dispatchEvent(new Event('submit'));
    }
  });

  // Envío de consulta
  dom.composerForm.addEventListener('submit', handleChatSubmit);

  // Selector de Marco Legal
  dom.selectFramework.addEventListener('change', async (e) => {
    const val = e.target.value;
    state.activeCorpus = val;
    updateContextLabel();
    if (val !== 'custom') {
      await switchCorpusOnServer(val);
      await loadCorpusPreview(val);
    }
  });

  // Toggle Búsqueda Web
  dom.toggleWebSearch.addEventListener('change', (e) => {
    state.enableWebSearch = e.target.checked;
  });

  // Chips sugeridos
  dom.suggestedQueries.addEventListener('click', (e) => {
    const chip = e.target.closest('.query-chip');
    if (!chip) return;
    dom.composerInput.value = chip.dataset.query;
    dom.composerInput.focus();
    dom.composerInput.dispatchEvent(new Event('input'));
  });

  // Subida de Archivos: Disparadores
  dom.btnTriggerUpload.addEventListener('click', () => dom.fileInput.click());
  dom.btnAttach.addEventListener('click', () => dom.globalFileInput.click());
  dom.dropzone.addEventListener('click', () => dom.fileInput.click());

  dom.fileInput.addEventListener('change', (e) => handleFileUpload(e.target.files[0]));
  dom.globalFileInput.addEventListener('change', (e) => handleFileUpload(e.target.files[0]));

  // Drag & Drop en Dropzone
  dom.dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dom.dropzone.classList.add('dragover');
  });
  dom.dropzone.addEventListener('dragleave', () => dom.dropzone.classList.remove('dragover'));
  dom.dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dom.dropzone.classList.remove('dragover');
    if (e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  });

  // Acciones sobre el Markdown generado
  dom.btnCopyMd.addEventListener('click', () => {
    if (!state.uploadedMarkdown) return;
    navigator.clipboard.writeText(state.uploadedMarkdown);
    dom.btnCopyMd.textContent = '¡Copiado!';
    setTimeout(() => dom.btnCopyMd.textContent = 'Copiar Markdown', 2000);
  });

  dom.btnDownloadMd.addEventListener('click', () => {
    if (!state.uploadedMarkdown) return;
    const blob = new Blob([state.uploadedMarkdown], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${state.uploadedDocName || 'documento'}.md`;
    a.click();
    URL.revokeObjectURL(url);
  });

  // Pestañas del Sidebar
  dom.tabBtnDoc.addEventListener('click', () => switchSidebarTab('document'));
  dom.tabBtnCitations.addEventListener('click', () => switchSidebarTab('citations'));

  // Drawer Móvil
  dom.btnToggleDrawer.addEventListener('click', () => dom.sidebar.classList.toggle('open'));
  dom.btnCloseSidebar.addEventListener('click', () => dom.sidebar.classList.remove('open'));

  // Modal API Key
  dom.btnOpenKeyModal.addEventListener('click', () => dom.modalKey.showModal());
  dom.btnCloseKeyModal.addEventListener('click', () => dom.modalKey.close());
  dom.btnSaveKey.addEventListener('click', () => {
    state.userApiKey = dom.inputGeminiKey.value.trim();
    sessionStorage.setItem('iuris_api_key', state.userApiKey);
    dom.modalKey.close();
  });
  dom.btnResetKey.addEventListener('click', () => {
    state.userApiKey = '';
    sessionStorage.removeItem('iuris_api_key');
    dom.inputGeminiKey.value = '';
    dom.modalKey.close();
  });
}

function switchSidebarTab(tab) {
  if (tab === 'document') {
    dom.tabBtnDoc.classList.add('active');
    dom.tabBtnCitations.classList.remove('active');
    dom.panelDoc.classList.add('active');
    dom.panelCitations.classList.remove('active');
  } else {
    dom.tabBtnCitations.classList.add('active');
    dom.tabBtnDoc.classList.remove('active');
    dom.panelCitations.classList.add('active');
    dom.panelDoc.classList.remove('active');
  }
}

function updateContextLabel() {
  if (state.activeCorpus === 'corporativo') {
    dom.activeContextLabel.textContent = 'Marco: Estatuto Corporativo & Cumplimiento';
  } else if (state.activeCorpus === 'lft') {
    dom.activeContextLabel.textContent = 'Marco: Ley Federal del Trabajo (LFT / Laboral)';
  } else if (state.activeCorpus === 'custom') {
    dom.activeContextLabel.textContent = `Expediente: ${state.uploadedDocName || 'Documento Subido'}`;
  }
}

// ==============================================================================
// 5. SUBIDA Y CONVERSIÓN DE DOCUMENTOS A MARKDOWN
// ==============================================================================
async function handleFileUpload(file) {
  if (!file) return;

  const validExts = ['.pdf', '.docx', '.doc', '.txt', '.md'];
  const ext = '.' + file.name.split('.').pop().toLowerCase();
  if (!validExts.includes(ext)) {
    alert(`Extensión no válida (${ext}). Sube archivos PDF, Word (.docx) o Texto (.txt, .md).`);
    return;
  }

  // Notificar al usuario en el chat
  appendMessage('assistant', `Iniciando conversión de <b>${escapeHtml(file.name)}</b> a Markdown estructurado...`);

  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await fetch(`${state.apiBase}/api/upload`, {
      method: 'POST',
      body: formData
    });

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || `HTTP ${res.status}`);
    }

    const data = await res.json();
    state.uploadedDocName = file.name;
    state.uploadedMarkdown = data.markdown;
    state.activeCorpus = 'custom';

    // Actualizar selector y ficha de metadatos
    dom.optCustomDoc.disabled = false;
    dom.optCustomDoc.textContent = `Expediente: ${file.name}`;
    dom.selectFramework.value = 'custom';
    updateContextLabel();

    dom.docMetaCard.style.display = 'block';
    dom.docNameLabel.textContent = file.name;
    dom.docTypeBadge.textContent = data.tipo;
    dom.docWordsStat.textContent = `${data.palabras.toLocaleString()} palabras`;
    dom.docSectionsStat.textContent = `${data.secciones_detectadas} secciones/cláusulas`;
    dom.markdownViewer.textContent = data.markdown;

    // Abrir panel lateral en escritorio o móvil
    switchSidebarTab('document');
    dom.sidebar.classList.add('open');

    appendMessage('assistant', `
      El documento <b>${escapeHtml(file.name)}</b> ha sido ingerido y convertido a <b>Markdown</b> con éxito.<br><br>
      • <b>Formato Original:</b> ${escapeHtml(data.tipo)}<br>
      • <b>Volumen:</b> ${data.palabras.toLocaleString()} palabras procesadas<br>
      • <b>Estructura:</b> ${data.secciones_detectadas} cláusulas/artículos indexados<br><br>
      El asistente ha anclado el contexto en este expediente. Puedes formular cualquier consulta legal sobre este contrato o solicitar un dictamen de riesgos.
    `);

  } catch (err) {
    appendMessage('assistant', `Fallo al procesar el archivo: <b>${escapeHtml(err.message)}</b>. Verifica que no tenga contraseñas ni esté corrupto.`);
  }
}

// ==============================================================================
// 6. CAMBIO DE MARCO LEGAL Y PREVISUALIZACIÓN DE CORPUS
// ==============================================================================
async function switchCorpusOnServer(corpusId) {
  try {
    await fetch(`${state.apiBase}/api/corpus/select`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ corpus_id: corpusId })
    });
  } catch (_) {}
}

async function loadCorpusPreview(corpusId) {
  try {
    const res = await fetch(`${state.apiBase}/api/corpus`);
    if (res.ok) {
      const data = await res.json();
      const mdContent = data.secciones.map(s => `## ${s.titulo}\n\n${s.contenido}\n`).join('\n---\n\n');
      dom.markdownViewer.textContent = mdContent || 'Sin contenido cargado.';
    }
  } catch (_) {
    dom.markdownViewer.textContent = 'Estructura normativa activa.';
  }
}

// ==============================================================================
// 7. INFERENCIA Y ENVÍO DE CONSULTAS
// ==============================================================================
async function handleChatSubmit(e) {
  e.preventDefault();
  const query = dom.composerInput.value.trim();
  if (!query || state.isProcessing) return;

  state.isProcessing = true;
  dom.btnSubmit.disabled = true;

  // Renderizar consulta de usuario
  appendMessage('user', query);
  dom.composerInput.value = '';
  dom.composerInput.style.height = 'auto';

  // Mostrar mensaje de carga institucional
  const loadingElement = appendLoadingMessage();

  try {
    const payload = {
      mensaje: query,
      enable_web_search: state.enableWebSearch,
      corpus: state.activeCorpus,
      api_key_override: state.userApiKey || null
    };

    const headers = { 'Content-Type': 'application/json' };
    if (state.userApiKey) headers['X-Gemini-Api-Key'] = state.userApiKey;

    const res = await fetch(`${state.apiBase}/api/chat`, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      throw new Error(`Error en el servidor: HTTP ${res.status}`);
    }

    const data = await res.json();
    loadingElement.remove();

    // Renderizar respuesta con fuentes
    appendMessage('assistant', data.respuesta, data.fuentes, data.fuentes_web);

    // Actualizar panel lateral de Citas & Fuentes
    updateCitationsSidebar(data.fuentes, data.fuentes_web);

  } catch (err) {
    loadingElement.remove();
    appendMessage('assistant', `No fue posible completar la inferencia: <b>${escapeHtml(err.message)}</b>. Comprueba la conectividad del servidor.`);
  } finally {
    state.isProcessing = false;
    dom.btnSubmit.disabled = false;
  }
}

// ==============================================================================
// 8. RENDERIZADO DE MENSAJES Y CITAS
// ==============================================================================
function appendMessage(role, content, fuentesLocales = [], fuentesWeb = []) {
  const row = document.createElement('div');
  row.className = `thread-message ${role === 'user' ? 'user-row' : 'assistant-row'}`;

  const authorName = role === 'user' ? 'Tú' : 'Iuris Legal Intelligence';
  const roleTitle = role === 'user' ? 'Consulta' : 'Asesor Jurídico';

  let citationsBlock = '';
  if (fuentesWeb && fuentesWeb.length > 0) {
    citationsBlock = `
      <div class="cited-sources-box">
        <div class="sources-label">Fuentes Oficiales y Legislación Consultada en Internet</div>
        ${fuentesWeb.map(fw => `
          <a href="${escapeHtml(fw.url)}" target="_blank" rel="noopener noreferrer" class="source-item-link">
            ⚖ ${escapeHtml(fw.titulo)}
          </a>
        `).join('')}
      </div>
    `;
  }

  row.innerHTML = `
    <div class="message-meta-line">
      <span class="meta-author">${authorName}</span>
      <span class="meta-time">${roleTitle}</span>
    </div>
    <div class="message-content">
      ${formatContent(content)}
      ${citationsBlock}
    </div>
  `;

  dom.chatThread.appendChild(row);
  dom.chatThread.scrollTop = dom.chatThread.scrollHeight;
  return row;
}

function appendLoadingMessage() {
  const row = document.createElement('div');
  row.className = 'thread-message assistant-row';
  row.innerHTML = `
    <div class="message-meta-line">
      <span class="meta-author">Iuris Legal Intelligence</span>
      <span class="meta-time">Analizando...</span>
    </div>
    <div class="message-content" style="color: var(--text-dim); display: flex; align-items: center; gap: 0.5rem;">
      <span style="display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: var(--accent-blue); animation: pulse 1s infinite;"></span>
      <span>Consultando jurisprudencia, marco normativo y articulado aplicable...</span>
    </div>
  `;
  dom.chatThread.appendChild(row);
  dom.chatThread.scrollTop = dom.chatThread.scrollHeight;
  return row;
}

function updateCitationsSidebar(fuentesLocales, fuentesWeb) {
  if ((!fuentesLocales || fuentesLocales.length === 0) && (!fuentesWeb || fuentesWeb.length === 0)) {
    dom.citationsList.innerHTML = '<p class="empty-citations-hint">No se recuperaron citas específicas para esta consulta.</p>';
    return;
  }

  let html = '';

  // Fuentes Web
  if (fuentesWeb && fuentesWeb.length > 0) {
    html += fuentesWeb.map(fw => `
      <div class="citation-card">
        <div class="citation-card-title">${escapeHtml(fw.titulo)}</div>
        <div class="citation-card-snippet">${escapeHtml(fw.snippet)}</div>
        <a href="${escapeHtml(fw.url)}" target="_blank" rel="noopener noreferrer" class="citation-card-link">
          Ver Decreto / Ley Oficial &rarr;
        </a>
      </div>
    `).join('');
  }

  // Fuentes Locales
  if (fuentesLocales && fuentesLocales.length > 0) {
    html += fuentesLocales.map(fl => `
      <div class="citation-card">
        <div class="citation-card-title">Cláusula Local / Expediente</div>
        <div class="citation-card-snippet">${escapeHtml(fl)}</div>
      </div>
    `).join('');
  }

  dom.citationsList.innerHTML = html;
}

function formatContent(text) {
  let html = escapeHtml(text);
  // Negritas **texto**
  html = html.replace(/\*\*(.*?)\*\*/g, '<b>$1</b>');
  // Viñetas •
  html = html.replace(/• (.*?)(?=(• |$|\n))/g, '<li>$1</li>');
  // Saltos de línea
  html = html.replace(/\n\n/g, '<p></p>');
  html = html.replace(/\n/g, '<br>');
  return html;
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// Inicializar la aplicación
document.addEventListener('DOMContentLoaded', init);
