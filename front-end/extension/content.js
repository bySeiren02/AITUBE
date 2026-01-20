// AI YouTube 쇼츠 분석기 - 통합 버전
// YouTube 쇼츠 감지 클래스
class YouTubeShowsDetector {
  constructor() {
    this.isShowsMode = false;
    this.currentVideoId = null;
    this.observer = null;
    this.videoObserver = null;
    this.callbacks = [];
    this.videoReadySent = new Set(); // 이미 videoReady를 보낸 비디오 ID 추적
  }

  // 쇼츠 모드 감지
  detectShowsMode() {
    const url = window.location.href;
    const pathname = window.location.pathname;
    
    // YouTube 쇼츠 URL 패턴 검사 (더 유연하게)
    const showsPatterns = [
      /\/shorts\/[^\/\?]+/,  // /shorts/로 시작하는 모든 경로
      /^https:\/\/www\.youtube\.com\/shorts\/[^\/\?]+/,
      /^https:\/\/youtube\.com\/shorts\/[^\/\?]+/,
      /^https:\/\/m\.youtube\.com\/shorts\/[^\/\?]+/,
    ];
    
    // 일반 비디오도 분석 대상에 포함
    const isVideoPage = /\/watch\?v=/.test(url) || /\/shorts\//.test(pathname);
    
    const isShows = showsPatterns.some(pattern => pattern.test(url) || pattern.test(pathname));
    
    // 쇼츠이거나 일반 비디오 페이지면 분석 대상
    if ((isShows || isVideoPage) && !this.isShowsMode) {
      this.isShowsMode = true;
      this.setupVideoDetection();
      this.notifyCallbacks('showsDetected');
      return true;
    } else if (!isShows && !isVideoPage && this.isShowsMode) {
      this.isShowsMode = false;
      this.cleanup();
      this.notifyCallbacks('showsEnded');
      return false;
    }
    return this.isShowsMode;
  }

  // 비디오 요소 감지 설정
  setupVideoDetection() {
    // 기존 비디오 감지
    this.detectExistingVideo();
    
    // 새로운 비디오 로드 감지 (SPA 대응)
    this.observer = new MutationObserver(() => {
      this.detectExistingVideo();
    });
    
    this.observer.observe(document.body, {
      childList: true,
      subtree: true
    });
  }

  // 기존 비디오 감지
  detectExistingVideo() {
    const video = document.querySelector('video');
    if (video) {
      const videoId = this.extractVideoId(video);
      
      // 비디오 ID가 변경되었는지 확인
      if (videoId && videoId !== this.currentVideoId) {
        // 이전 비디오의 ready 플래그 제거
        this.videoReadySent.clear();
        this.currentVideoId = videoId;
        this.notifyCallbacks('videoChange', { video, videoId: this.currentVideoId });
        
        // 비디오가 준비되었는지 확인 (아직 ready를 보내지 않은 경우만)
        if (video.readyState >= 2 && !this.videoReadySent.has(videoId)) {
          this.videoReadySent.add(videoId);
          this.notifyCallbacks('videoReady', { video, videoId: this.currentVideoId });
        } else if (video.readyState < 2 && !this.videoReadySent.has(videoId)) {
          // 비디오 로드 대기 (한 번만)
          const onLoadedData = () => {
            video.removeEventListener('loadeddata', onLoadedData);
            if (!this.videoReadySent.has(videoId)) {
              this.videoReadySent.add(videoId);
              this.notifyCallbacks('videoReady', { video, videoId: this.currentVideoId });
            }
          };
          video.addEventListener('loadeddata', onLoadedData, { once: true });
        }
      } else if (videoId && videoId === this.currentVideoId) {
        // 같은 비디오지만 아직 준비되지 않았을 수 있음 (한 번만)
        if (video.readyState >= 2 && !this.videoReadySent.has(videoId)) {
          this.videoReadySent.add(videoId);
          this.notifyCallbacks('videoReady', { video, videoId: this.currentVideoId });
        }
      }
    }
  }

  // video ID 추출
  extractVideoId(video) {
    // pathname에서 추출 (더 정확)
    const pathnameMatch = window.location.pathname.match(/\/shorts\/([a-zA-Z0-9_-]+)/);
    if (pathnameMatch) {
      return pathnameMatch[1];
    }
    
    // URL에서 추출
    const urlMatch = window.location.href.match(/\/shorts\/([a-zA-Z0-9_-]+)/);
    if (urlMatch) {
      return urlMatch[1];
    }
    
    // 일반 비디오 URL에서 추출
    const urlParams = new URLSearchParams(window.location.search);
    const videoId = urlParams.get('v');
    if (videoId) {
      return videoId;
    }
    
    return '';
  }

  // 콜백 등록
  onShowsDetected(callback) {
    this.callbacks.push({ event: 'showsDetected', callback });
  }

  onShowsEnded(callback) {
    this.callbacks.push({ event: 'showsEnded', callback });
  }

  onVideoChange(callback) {
    this.callbacks.push({ event: 'videoChange', callback });
  }

  onVideoReady(callback) {
    this.callbacks.push({ event: 'videoReady', callback });
  }

  // 콜백 알림
  notifyCallbacks(event, data) {
    this.callbacks.forEach(item => {
      if (item.event === event && typeof item.callback === 'function') {
        item.callback(data);
      }
    });
  }

  // 정리
  cleanup() {
    if (this.observer) {
      this.observer.disconnect();
      this.observer = null;
    }
    
    this.isShowsMode = false;
    this.currentVideoId = null;
    this.callbacks = [];
    this.videoReadySent.clear();
  }

  // 현재 video 정보
  getCurrentVideo() {
    return {
      video: document.querySelector('video'),
      videoId: this.currentVideoId
    };
  }
}

// 비디오 프레임 캡처 클래스
class VideoFrameCapture {
  constructor(video) {
    this.video = video;
    this.canvas = document.createElement('canvas');
    this.ctx = this.canvas.getContext('2d');
    this.capturedFrames = [];
  }

  // 대표 프레임 캡처 (10장)
  async captureRepresentativeFrames() {
    console.log('[AITUBE] 프레임 캡처 시작');
    
    if (!this.video || this.video.readyState < 2) {
      throw new Error('비디오가 준비되지 않았습니다');
    }

    const duration = this.video.duration;
    
    if (!duration || duration === Infinity || isNaN(duration)) {
      throw new Error('비디오 길이를 가져올 수 없습니다');
    }

    // 캡처할 시간대 계산
    const captureTimes = this.calculateCaptureTimes(duration);
    console.log(`[AITUBE] 캡처 시간대:`, captureTimes);

    this.capturedFrames = []; // 초기화

    // 각 시간대별로 프레임 캡처
    for (let i = 0; i < captureTimes.length; i++) {
      const time = captureTimes[i];
      
      try {
        console.log(`[AITUBE] 프레임 캡처 중: ${time.toFixed(2)}초`);
        
        // 비디오 탐색
        await this.waitForSeek(time);
        
        // 프레임 캡처
        const frame = await this.captureFrame();
        
        if (frame) {
          this.capturedFrames.push(frame);
          console.log(`[AITUBE] 프레임 ${i + 1}/${captureTimes.length} 캡처 완료`);
        } else {
          console.warn(`[AITUBE] 프레임 ${i + 1} 캡처 실패 (null)`);
        }
      } catch (error) {
        console.error(`[AITUBE] 프레임 ${i + 1} 캡처 중 오류:`, error);
        // 일부 프레임 실패해도 계속 진행
      }
    }
    
    if (this.capturedFrames.length === 0) {
      throw new Error('모든 프레임 캡처 실패');
    }
    
    console.log(`[AITUBE] 총 ${this.capturedFrames.length}개 프레임 캡처 완료`);
    return this.capturedFrames;
  }

  // 캡처 시간 계산
  calculateCaptureTimes(duration) {
    const frameCount = 10; // 10개로 증가
    
    if (duration < 30) {
      // Shorts: 전체 길이에 걸쳐 균등 분배
      const times = [];
      for (let i = 1; i <= frameCount; i++) {
        times.push((duration * i) / (frameCount + 1));
      }
      return times;
    } else {
      // 일반 영상: 전체 길이에 걸쳐 균등 분배 (시작 5초, 끝 5초 제외)
      const times = [];
      const startOffset = 5;
      const endOffset = 5;
      const availableDuration = duration - startOffset - endOffset;
      
      for (let i = 1; i <= frameCount; i++) {
        times.push(startOffset + (availableDuration * i) / (frameCount + 1));
      }
      return times;
    }
  }

  // 프레임 캡처
  async captureFrame() {
    return new Promise((resolve, reject) => {
      try {
        // 비디오 크기에 맞춰 캔버스 크기 조정
        const videoWidth = this.video.videoWidth || 320;
        const videoHeight = this.video.videoHeight || 240;
        
        // 비율 유지하면서 최대 크기 설정
        const maxWidth = 320;
        const maxHeight = 240;
        let canvasWidth = videoWidth;
        let canvasHeight = videoHeight;
        
        if (canvasWidth > maxWidth) {
          canvasHeight = (canvasHeight * maxWidth) / canvasWidth;
          canvasWidth = maxWidth;
        }
        if (canvasHeight > maxHeight) {
          canvasWidth = (canvasWidth * maxHeight) / canvasHeight;
          canvasHeight = maxHeight;
        }
        
        this.canvas.width = canvasWidth;
        this.canvas.height = canvasHeight;
        
        // 비디오가 로드되지 않았으면 에러
        if (this.video.readyState < 2) {
          reject(new Error('비디오가 아직 로드되지 않았습니다'));
          return;
        }
        
        this.ctx.drawImage(this.video, 0, 0, canvasWidth, canvasHeight);
        
        this.canvas.toBlob((blob) => {
          if (blob) {
            resolve(blob);
          } else {
            reject(new Error('프레임을 Blob으로 변환 실패'));
          }
        }, 'image/jpeg', 0.85); // JPEG 품질 85%
        
      } catch (error) {
        reject(error);
      }
    });
  }

  // 비디오 탐임 대기
  async waitForSeek(targetTime) {
    return new Promise((resolve, reject) => {
      // 이미 해당 시간에 있으면 바로 resolve
      if (Math.abs(this.video.currentTime - targetTime) < 0.1) {
        resolve();
        return;
      }

      let timeoutId;
      const maxWaitTime = 5000; // 최대 5초 대기
      
      const seeked = () => {
        clearTimeout(timeoutId);
        this.video.removeEventListener('seeked', seeked);
        this.video.removeEventListener('error', onError);
        
        // seek 완료 후 약간의 지연을 주어 프레임이 렌더링되도록 함
        setTimeout(() => {
          resolve();
        }, 100);
      };
      
      const onError = () => {
        clearTimeout(timeoutId);
        this.video.removeEventListener('seeked', seeked);
        this.video.removeEventListener('error', onError);
        reject(new Error('비디오 탐색 실패'));
      };
      
      // 타임아웃 설정
      timeoutId = setTimeout(() => {
        this.video.removeEventListener('seeked', seeked);
        this.video.removeEventListener('error', onError);
        reject(new Error('비디오 탐색 타임아웃'));
      }, maxWaitTime);
      
      this.video.addEventListener('seeked', seeked);
      this.video.addEventListener('error', onError);
      
      // 비디오 탐색 시작
      this.video.currentTime = targetTime;
    });
  }
}

// API 통신 모듈
class APIAnalyzer {
  constructor() {
    this.apiEndpoint = 'http://localhost:8005/api/analyze';
    this.timeout = 30000; // 30초 타임아웃
    this.maxRetries = 2;
    this.isAnalyzing = false;
    this.loadSettings();
  }

  // 설정 로드
  async loadSettings() {
    try {
      const settings = await chrome.storage.local.get({
        apiEndpoint: 'http://localhost:8005/api/analyze'
      });
      if (settings.apiEndpoint) {
        this.apiEndpoint = settings.apiEndpoint;
      }
    } catch (error) {
      console.error('[AITUBE] 설정 로드 실패:', error);
    }
  }

  // 프레임 분석 요청
  async analyzeFrames(frames, videoMetadata) {
    if (this.isAnalyzing) {
      throw new Error('이미 분석 중입니다');
    }

    this.isAnalyzing = true;
    console.log('[AITUBE] API 분석 시작:', { frameCount: frames.length, metadata: videoMetadata });

    try {
      // 프레임 데이터 준비
      const frameData = await this.prepareFrameData(frames);
      
      const requestBody = {
        frames: frameData,
        metadata: {
          duration: videoMetadata.duration,
          title: videoMetadata.title,
          videoId: videoMetadata.videoId,
          url: videoMetadata.url,
          timestamp: Date.now()
        }
      };
      
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), this.timeout);
      
      const response = await fetch(this.apiEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestBody),
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      
      if (!response.ok) {
        throw new Error(`API 응답 오류: ${response.status} ${response.statusText}`);
      }
      
      const result = await response.json();
      
      if (!result) {
        throw new Error('API 응답이 비어있습니다');
      }
      
      return this.parseAPIResponse(result);
      
    } catch (error) {
      console.error('[AITUBE] API 분석 실패:', error);
      if (error.name === 'AbortError') {
        throw new Error('API 요청 타임아웃 (30초 초과)');
      }
      if (error.message && error.message.includes('Failed to fetch')) {
        // 네트워크 오류인 경우 더 자세한 안내
        const errorMsg = `⚠️ API 서버에 연결할 수 없습니다\n\n` +
          `📡 엔드포인트: ${this.apiEndpoint}\n\n` +
          `💡 해결 방법:\n` +
          `1. API 서버가 실행 중인지 확인하세요\n` +
          `2. 확장 프로그램 설정에서 API 엔드포인트를 확인하세요\n` +
          `3. 방화벽이나 네트워크 설정을 확인하세요`;
        throw new Error(errorMsg);
      }
      throw error;
    } finally {
      this.isAnalyzing = false;
    }
  }

  // 프레임 데이터 준비
  async prepareFrameData(frames) {
    const frameData = [];
    
    for (const frame of frames) {
      if (frame instanceof Blob) {
        // Blob을 base64로 변환
        const base64 = await this.blobToBase64(frame);
        frameData.push({
          data: base64,
          type: 'base64',
          size: frame.size
        });
      } else if (frame instanceof HTMLCanvasElement) {
        frameData.push({
          data: frame.toDataURL('image/jpeg', 0.85),
          type: 'dataurl',
          size: 0
        });
      }
    }
    
    return frameData;
  }

  // Blob을 base64로 변환
  blobToBase64(blob) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        // data:image/jpeg;base64, 부분 제거하고 base64만 반환
        const base64 = reader.result.split(',')[1];
        resolve(base64);
      };
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  }

  // API 응답 파싱
  parseAPIResponse(apiResponse) {
    if (!apiResponse) {
      throw new Error('API 응답이 없습니다');
    }

    return {
      videoId: apiResponse.videoId || '',
      isAiGenerated: apiResponse.is_ai_generated || false,
      aiConfidence: this.normalizeConfidence(apiResponse.ai_confidence || 0),
      aiModel: apiResponse.ai_model || null,
      confidence: this.normalizeConfidence(apiResponse.confidence || 0),
      detectedSigns: apiResponse.detected_signs || [],
      summary: apiResponse.summary || '',
      analysisTime: apiResponse.analysis_time || 0,
      model: apiResponse.model || 'unknown',
      timestamp: apiResponse.timestamp || Date.now()
    };
  }


  // 신뢰도 정규화
  normalizeConfidence(confidence) {
    if (typeof confidence !== 'number') return 0.5;
    return Math.min(1.0, Math.max(0, confidence));
  }

  // 특징 포맷
  formatFeatures(features) {
    return Array.isArray(features) ? features.join(', ') : '';
  }

  // 캐시된 분석 로드
  async loadCachedAnalysis(videoId) {
    try {
      const result = await chrome.storage.local.get(`analysis_${videoId}`);
      return result[`analysis_${videoId}`] || null;
    } catch (error) {
      console.error('[AITUBE] 캐시 로드 실패:', error);
      return null;
    }
  }

  // 분석 결과 처리
  async processAnalysisResult(result, overlayUI) {
    try {
      // 캐시 저장
      await this.saveAnalysisResult(result);
      
      // 오버레이 표시
      if (overlayUI && result) {
        overlayUI.showAnalysisResult(result);
      }
    } catch (error) {
      console.error('[AITUBE] 분석 결과 처리 실패:', error);
    }
  }

  // 분석 결과 저장
  async saveAnalysisResult(result) {
    try {
      const key = `analysis_${result.videoId}`;
      await chrome.storage.local.set({ [key]: result });
    } catch (error) {
      console.error('[AITUBE] 분석 저장 실패:', error);
    }
  }

  // 서버 상태 확인
  async checkServerStatus() {
    try {
      const response = await fetch(`${this.apiEndpoint}/status`, {
        method: 'GET'
      });
      
      if (response.ok) {
        return {
          status: 'connected',
          message: '서버 연결됨'
        };
      } else {
        return {
          status: 'disconnected',
          message: '서버 연결 실패'
        };
      }
    } catch (error) {
      return {
        status: 'error',
        message: `서버 상태 확인 실패: ${error.message}`
      };
    }
  }

  // 캐시 정리
  async clearOldCache() {
    try {
      const all = await chrome.storage.local.get();
      const oneDayAgo = Date.now() - (24 * 60 * 60 * 1000);
      
      for (const key in all) {
        if (key.startsWith('analysis_') && all[key]) {
          const analysis = all[key];
          if (analysis.timestamp && analysis.timestamp < oneDayAgo) {
            await chrome.storage.local.remove(key);
          }
        }
      }
    } catch (error) {
      console.error('[AITUBE] 캐시 정리 실패:', error);
    }
  }
}

// 오버레이 UI 관리 클래스
class OverlayUI {
  constructor() {
    this.overlay = null;
    this.status = 'idle';
    this.isVisible = false;
    this.currentResult = null;
  }

  // 오버레이 생성 및 삽입
  createOverlay() {
    if (this.overlay) {
      this.show();
      return;
    }

    this.overlay = document.createElement('div');
    this.overlay.id = 'ai-shows-analyzer-overlay';
    this.overlay.innerHTML = `
      <div class="ai-analyzer-header">
        <div class="ai-analyzer-status">
          <div class="status-icon idle">⏸️</div>
          <div class="status-text">준비중</div>
        </div>
        <button class="ai-analyzer-close" aria-label="닫기">×</button>
      </div>
      <div class="ai-analyzer-content">
        <div id="status-message" class="analysis-status-message" style="display: none;">
          <div class="loading-spinner"></div>
          <span>AI 생성 여부를 분석중입니다...</span>
        </div>
        <div class="ai-analysis-result" style="display: none;">
          <div class="result-header">
            <h3>🤖 AI 생성 여부 분석</h3>
          </div>
          <div class="result-content">
            <div class="ai-detection-result">
              <div class="ai-status-badge" id="ai-status-badge">
                <span class="ai-status-icon">🤖</span>
                <span class="ai-status-text">분석 중...</span>
              </div>
              <div class="ai-confidence">
                <strong>AI 생성 확률:</strong>
                <span class="confidence-value" id="ai-confidence-value">-</span>
              </div>
              <div class="ai-model" id="ai-model-section" style="display: none;">
                <strong>추정 AI 모델:</strong>
                <span class="ai-model-value" id="ai-model-value">-</span>
              </div>
              <div class="detected-signs" id="detected-signs-section" style="display: none;">
                <strong>감지된 징후:</strong>
                <div class="signs-list" id="signs-list">-</div>
              </div>
              <div class="analysis-summary">
                <strong>분석 요약:</strong>
                <span class="summary-value" id="summary-value">-</span>
              </div>
            </div>
          </div>
        </div>
        <div class="ai-error-message" id="ai-error-message" style="display: none;">
          <div class="error-content" id="error-content"></div>
        </div>
      </div>
    `;
    
    document.body.appendChild(this.overlay);
    this.setupEventListeners();
  }

  // 이벤트 리스너 설정
  setupEventListeners() {
    const closeBtn = this.overlay.querySelector('.ai-analyzer-close');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => this.hide());
    }
  }

  // 상태 업데이트
  updateStatus(status, message = '') {
    const statusIcon = this.overlay.querySelector('.status-icon');
    const statusText = this.overlay.querySelector('.status-text');
    const statusMessage = this.overlay.querySelector('#status-message');
    const analysisResult = this.overlay.querySelector('.ai-analysis-result');
    
    // 상태 아이콘 설정
    const statusIcons = {
      idle: '⏸️',
      loading: '⏳️',
      analyzing: '🔍',
      success: '✅',
      error: '❌'
    };
    
    statusIcon.textContent = statusIcons[status] || statusIcons.idle;
    statusText.textContent = message || '준비중';
    
    // 상태 메시지 표시
    if (status === 'loading' || status === 'capturing' || status === 'analyzing') {
      if (statusMessage) {
        statusMessage.style.display = 'block';
        const statusText = statusMessage.querySelector('span');
        if (statusText) {
          statusText.textContent = message || 'AI 생성 여부를 분석중입니다...';
        }
      }
      if (analysisResult) {
        analysisResult.style.display = 'none';
      }
    } else if (status === 'success') {
      if (statusMessage) {
        statusMessage.style.display = 'none';
      }
      if (analysisResult) {
        analysisResult.style.display = 'block';
      }
      const errorMessage = this.overlay.querySelector('#ai-error-message');
      if (errorMessage) {
        errorMessage.style.display = 'none';
      }
    } else if (status === 'error') {
      if (statusMessage) {
        statusMessage.style.display = 'none';
      }
      if (analysisResult) {
        analysisResult.style.display = 'none';
      }
      // 오류 메시지 표시
      const errorMessage = this.overlay.querySelector('#ai-error-message');
      const errorContent = this.overlay.querySelector('#error-content');
      if (errorMessage && errorContent) {
        errorMessage.style.display = 'block';
        // 줄바꿈을 <br>로 변환
        errorContent.innerHTML = (message || '오류가 발생했습니다').replace(/\n/g, '<br>');
      }
    } else {
      if (statusMessage) {
        statusMessage.style.display = 'none';
      }
      if (analysisResult) {
        analysisResult.style.display = 'none';
      }
    }
    
    this.status = status;
  }

  // 분석 결과 표시
  showAnalysisResult(result) {
    if (!result) {
      console.error('[AITUBE] 분석 결과가 없습니다');
      return;
    }

    if (!this.overlay) {
      this.createOverlay();
    }
    
    this.currentResult = result;
    this.isVisible = true;
    
    const analysisResult = this.overlay.querySelector('.ai-analysis-result');
    const aiStatusBadge = this.overlay.querySelector('#ai-status-badge');
    const aiStatusIcon = this.overlay.querySelector('.ai-status-icon');
    const aiStatusText = this.overlay.querySelector('.ai-status-text');
    const aiConfidenceValue = this.overlay.querySelector('#ai-confidence-value');
    const aiModelSection = this.overlay.querySelector('#ai-model-section');
    const aiModelValue = this.overlay.querySelector('#ai-model-value');
    const detectedSignsSection = this.overlay.querySelector('#detected-signs-section');
    const signsList = this.overlay.querySelector('#signs-list');
    const summaryValue = this.overlay.querySelector('#summary-value');
    
    if (!analysisResult || !aiStatusBadge || !aiStatusIcon || !aiStatusText || !aiConfidenceValue) {
      console.error('[AITUBE] 오버레이 요소를 찾을 수 없습니다');
      return;
    }
    
    // AI 생성 여부 표시
    const isAiGenerated = result.isAiGenerated || false;
    const confidence = Math.round((result.aiConfidence || 0) * 100);
    
    if (isAiGenerated) {
      aiStatusBadge.className = 'ai-status-badge ai-detected';
      if (aiStatusIcon) aiStatusIcon.textContent = '🤖';
      if (aiStatusText) aiStatusText.textContent = 'AI 생성 영상으로 판단됨';
      aiStatusBadge.style.background = 'rgba(244, 67, 54, 0.1)';
      aiStatusBadge.style.borderColor = '#f44336';
      aiStatusBadge.style.color = '#d32f2f';
    } else {
      aiStatusBadge.className = 'ai-status-badge ai-not-detected';
      if (aiStatusIcon) aiStatusIcon.textContent = '✅';
      if (aiStatusText) aiStatusText.textContent = '실제 영상으로 판단됨';
      aiStatusBadge.style.background = 'rgba(76, 175, 80, 0.1)';
      aiStatusBadge.style.borderColor = '#4CAF50';
      aiStatusBadge.style.color = '#388E3C';
    }
    
    // AI 생성 확률
    if (aiConfidenceValue) {
      aiConfidenceValue.textContent = `${confidence}%`;
    }
    
    // AI 모델 정보
    if (result.aiModel && aiModelSection && aiModelValue) {
      aiModelSection.style.display = 'block';
      aiModelValue.textContent = result.aiModel;
    } else if (aiModelSection) {
      aiModelSection.style.display = 'none';
    }
    
    // 감지된 징후
    if (result.detectedSigns && Array.isArray(result.detectedSigns) && result.detectedSigns.length > 0) {
      if (detectedSignsSection && signsList) {
        detectedSignsSection.style.display = 'block';
        signsList.innerHTML = result.detectedSigns.map(sign => 
          `<span class="sign-tag">${sign}</span>`
        ).join('');
      }
    } else if (detectedSignsSection) {
      detectedSignsSection.style.display = 'none';
    }
    
    // 요약
    if (summaryValue) {
      summaryValue.textContent = result.summary || '분석 요약 없음';
    }
    
    // 상태 업데이트
    this.updateStatus('success', '분석 완료');
    
    // 표시
    analysisResult.style.display = 'block';
  }

  // 오버레이 표시
  show() {
    if (this.overlay) {
      this.overlay.style.display = 'block';
      this.isVisible = true;
    }
  }

  // 오버레이 숨김
  hide() {
    if (this.overlay) {
      this.overlay.style.display = 'none';
      this.isVisible = false;
    }
  }

  // 오버레이 제거
  cleanup() {
    if (this.overlay) {
      this.overlay.remove();
      this.overlay = null;
    }
    
    this.status = 'idle';
    this.isVisible = false;
    this.currentResult = null;
  }

  // 현재 표시 상태
  isShown() {
    return this.overlay && this.overlay.style.display !== 'none';
  }

  // 현재 결과
  getCurrentResult() {
    return this.currentResult;
  }
}

// 메인 AI YouTube 쇼츠 분석기 클래스
class AIShowsAnalyzer {
  constructor() {
    this.detector = null;
    this.overlayUI = null;
    this.apiAnalyzer = null;
    this.frameCapture = null;
    this.isAnalyzing = false;
    this.currentVideo = null;
    this.retryCount = 0;
    this.maxRetries = 3;
  }

// 초기화
async init() {
  console.log('[AITUBE] AI YouTube 쇼츠 분석기 초기화');
  
  try {
    // 각 모듈 초기화
    this.detector = new YouTubeShowsDetector();
    this.overlayUI = new OverlayUI();
    this.apiAnalyzer = new APIAnalyzer();
    
    // 이벤트 리스너 설정
    this.setupEventListeners();
    
    // URL 변경 감지 (SPA 대응)
    this.setupURLChangeDetection();
    
    // 초기 쇼츠 모드 감지
    if (this.detector.detectShowsMode()) {
      console.log('[AITUBE] YouTube 쇼츠/비디오 모드 감지됨');
      await this.setupForAnalysis();
    } else {
      console.log('[AITUBE] 일반 YouTube 페이지 (비디오 모드 아님)');
    }
    
  } catch (error) {
    console.error('[AITUBE] 초기화 실패:', error);
  }
}

// URL 변경 감지 설정
setupURLChangeDetection() {
  let lastUrl = window.location.href;
  
  // MutationObserver로 URL 변경 감지
  const observer = new MutationObserver(() => {
    const currentUrl = window.location.href;
    if (currentUrl !== lastUrl) {
      lastUrl = currentUrl;
      console.log('[AITUBE] URL 변경 감지:', currentUrl);
      
      // 약간의 지연 후 다시 감지 (DOM 업데이트 대기)
      setTimeout(() => {
        if (this.detector.detectShowsMode()) {
          console.log('[AITUBE] YouTube 쇼츠/비디오 모드 감지됨 (URL 변경 후)');
          this.setupForAnalysis();
        } else {
          console.log('[AITUBE] 일반 페이지로 변경됨');
          this.cleanup();
        }
      }, 500);
    }
  });
  
  observer.observe(document.body, {
    childList: true,
    subtree: true
  });
  
  // popstate 이벤트도 감지 (뒤로가기/앞으로가기)
  window.addEventListener('popstate', () => {
    setTimeout(() => {
      if (this.detector.detectShowsMode()) {
        console.log('[AITUBE] YouTube 쇼츠/비디오 모드 감지됨 (popstate)');
        this.setupForAnalysis();
      } else {
        this.cleanup();
      }
    }, 500);
  });
  
  // pushState/replaceState 감지
  const originalPushState = history.pushState;
  const originalReplaceState = history.replaceState;
  
  history.pushState = (...args) => {
    originalPushState.apply(history, args);
    setTimeout(() => {
      if (this.detector.detectShowsMode()) {
        console.log('[AITUBE] YouTube 쇼츠/비디오 모드 감지됨 (pushState)');
        this.setupForAnalysis();
      } else {
        this.cleanup();
      }
    }, 500);
  };
  
  history.replaceState = (...args) => {
    originalReplaceState.apply(history, args);
    setTimeout(() => {
      if (this.detector.detectShowsMode()) {
        console.log('[AITUBE] YouTube 쇼츠/비디오 모드 감지됨 (replaceState)');
        this.setupForAnalysis();
      } else {
        this.cleanup();
      }
    }, 500);
  };
} 

  // 분석 준비 설정
async setupForAnalysis() {
  try {
    // 오버레이 UI 생성
    this.overlayUI.createOverlay();
    this.overlayUI.updateStatus('idle');
    
    // 기존 분석 결과 확인
    const currentVideo = this.detector.getCurrentVideo();
    if (currentVideo && currentVideo.videoId) {
      const cachedResult = await this.apiAnalyzer.loadCachedAnalysis(currentVideo.videoId);
      
      if (cachedResult) {
        console.log('[AITUBE] 캐시된 분석 결과 발견:', currentVideo.videoId);
        this.overlayUI.showAnalysisResult(cachedResult);
      } else {
        console.log('[AITUBE] 새로운 영상 분석 준비 완료');
        this.overlayUI.updateStatus('idle');
        
        // 비디오가 준비되었는지 확인하고 자동 분석 시작
        if (currentVideo.video) {
          this.currentVideo = currentVideo.video;
          
          // 비디오가 로드되었는지 확인
          if (currentVideo.video.readyState >= 2) {
            // 비디오가 준비됨 - 자동 분석 시작
            if (this.shouldAutoAnalyze()) {
              setTimeout(() => {
                this.startAnalysis(currentVideo.videoId);
              }, 2000);
            }
          } else {
            // 비디오 로드 대기
            const onLoadedData = () => {
              currentVideo.video.removeEventListener('loadeddata', onLoadedData);
              if (this.shouldAutoAnalyze()) {
                setTimeout(() => {
                  this.startAnalysis(currentVideo.videoId);
                }, 2000);
              }
            };
            currentVideo.video.addEventListener('loadeddata', onLoadedData);
          }
        }
      }
    } else {
      // 비디오가 아직 없음 - MutationObserver가 감지할 때까지 대기
      console.log('[AITUBE] 비디오 요소 대기 중...');
    }
    
  } catch (error) {
    console.error('[AITUBE] 분석 준비 실패:', error);
    this.overlayUI.updateStatus('error', '분석 준비 중 오류 발생');
  }
}

  // 이벤트 리스너 설정
  setupEventListeners() {
    // YouTube 쇼츠 감지 이벤트
    this.detector.onShowsDetected(() => {
      console.log('[AITUBE] 쇼츠 시작됨');
      this.setupForAnalysis();
    });

    this.detector.onShowsEnded(() => {
      console.log('[AITUBE] 쇼츠 종료됨');
      this.cleanup();
    });

    // 비디오 변경 이벤트
    this.detector.onVideoChange(async ({ video, videoId }) => {
      console.log('[AITUBE] 비디오 변경:', videoId);
      await this.handleVideoChange(video, videoId);
    });

    // 비디오 준비 완료 이벤트
    this.detector.onVideoReady(async ({ video, videoId }) => {
      console.log('[AITUBE] 비디오 준비 완료:', videoId);
      this.currentVideo = video;
      
      // 자동 분석 시작 (옵션 기반)
      if (this.shouldAutoAnalyze()) {
        setTimeout(() => {
          this.startAnalysis(videoId);
        }, 2000); // 2초 후 자동 시작
      }
    });
  }

  // 비디오 변경 처리
  async handleVideoChange(video, videoId) {
    try {
      // 이전 분석 중단
      this.cancelCurrentAnalysis();
      
      // 현재 비디오 업데이트
      this.currentVideo = video;
      
      // 기존 분석 결과 확인
      const cachedResult = await this.apiAnalyzer.loadCachedAnalysis(videoId);
      
      if (cachedResult) {
        console.log('[AITUBE] 캐시된 결과 사용:', videoId);
        this.overlayUI.showAnalysisResult(cachedResult);
      } else {
        console.log('[AITUBE] 새로운 영상 준비 완료');
        this.overlayUI.updateStatus('idle');
        
        // 비디오가 준비되었는지 확인
        if (video && video.readyState >= 2) {
          // 자동 분석
          if (this.shouldAutoAnalyze()) {
            setTimeout(() => {
              this.startAnalysis(videoId);
            }, 1000);
          }
        } else if (video) {
          // 비디오 로드 대기
          const onLoadedData = () => {
            video.removeEventListener('loadeddata', onLoadedData);
            if (this.shouldAutoAnalyze()) {
              setTimeout(() => {
                this.startAnalysis(videoId);
              }, 1000);
            }
          };
          video.addEventListener('loadeddata', onLoadedData);
        }
      }
      
    } catch (error) {
      console.error('[AITUBE] 비디오 변경 처리 실패:', error);
      this.overlayUI.updateStatus('error', '비디오 변경 중 오류 발생');
    }
  }

  // 분석 시작
  async startAnalysis(videoId) {
    if (this.isAnalyzing) {
      console.log('[AITUBE] 분석 이미 진행 중');
      return;
    }

    if (!this.currentVideo) {
      console.warn('[AITUBE] 비디오 없음 - 분석 중단');
      return;
    }

    // 같은 비디오에 대한 중복 분석 방지
    if (this.analyzingVideoId === videoId && this.isAnalyzing) {
      console.log('[AITUBE] 같은 비디오 분석 이미 진행 중:', videoId);
      return;
    }

    this.isAnalyzing = true;
    this.analyzingVideoId = videoId;
    this.retryCount = 0;
    
    console.log('[AITUBE] AI 생성 여부 분석 시작:', videoId);
    this.overlayUI.show();
    
    try {
      // 프레임 캡처
      this.overlayUI.updateStatus('capturing', '영상 프레임을 캡처중입니다...');
      
      const frameCapture = new VideoFrameCapture(this.currentVideo);
      const frames = await frameCapture.captureRepresentativeFrames();
      
      if (frames.length === 0) {
        throw new Error('프레임 캡처 실패');
      }
      
      console.log(`[AITUBE] ${frames.length}개 프레임 캡처 완료`);
      
      // API 분석 요청
      this.overlayUI.updateStatus('analyzing', 'AI 생성 여부를 분석중입니다...');
      
      const videoMetadata = {
        duration: this.currentVideo.duration,
        title: document.title,
        videoId: videoId,
        url: window.location.href
      };
      
      const result = await this.apiAnalyzer.analyzeFrames(frames, videoMetadata);
      
      if (!result) {
        throw new Error('분석 결과가 없습니다');
      }
      
      // 결과 처리
      await this.apiAnalyzer.processAnalysisResult(result, this.overlayUI);
      
      console.log('[AITUBE] 분석 완료:', videoId);
      
      // 재시도 카운터 리셋
      this.retryCount = 0;
      this.analyzingVideoId = null;
      
    } catch (error) {
      console.error('[AITUBE] 분석 실패:', error);
      
      // 사용자 친화적인 오류 메시지
      let errorMessage = error.message || '분석 중 오류 발생';
      if (errorMessage.includes('서버에 연결할 수 없습니다')) {
        // 이미 API 엔드포인트가 메시지에 포함되어 있으면 그대로 사용
        if (!errorMessage.includes('엔드포인트:')) {
          errorMessage = `⚠️ API 서버에 연결할 수 없습니다\n\n📡 엔드포인트: ${this.apiAnalyzer.apiEndpoint}\n\n💡 해결 방법:\n1. API 서버가 실행 중인지 확인하세요\n2. 확장 프로그램 설정에서 API 엔드포인트를 확인하세요\n3. 방화벽이나 네트워크 설정을 확인하세요`;
        }
      } else if (errorMessage.includes('타임아웃')) {
        errorMessage = '⏱️ API 요청이 타임아웃되었습니다.\n서버 응답이 너무 느립니다.';
      }
      
      this.overlayUI.updateStatus('error', errorMessage);
      
      // 재시도 로직 (네트워크 오류가 아닌 경우에만)
      if (this.retryCount < this.maxRetries && !errorMessage.includes('서버에 연결할 수 없습니다')) {
        this.retryCount++;
        console.log(`[AITUBE] 분석 재시도 ${this.retryCount}/${this.maxRetries}`);
        
        setTimeout(() => {
          this.startAnalysis(videoId);
        }, 2000 * this.retryCount);
      } else {
        // 재시도 실패 시 상태 리셋
        this.isAnalyzing = false;
        this.analyzingVideoId = null;
      }
    } finally {
      // 재시도 중이 아닐 때만 isAnalyzing을 false로 설정
      if (this.retryCount >= this.maxRetries || this.retryCount === 0) {
        this.isAnalyzing = false;
        this.analyzingVideoId = null;
      }
    }
  }

  // 현재 분석 중단
  cancelCurrentAnalysis() {
    this.isAnalyzing = false;
    this.analyzingVideoId = null;
    this.retryCount = 0;
    console.log('[AITUBE] 현재 분석 중단');
  }

  // 자동 분석 여부 결정
  shouldAutoAnalyze() {
    return true; // TODO: 사용자 설정 기능 추가 가능
  }

  // 쇼츠 분석 수동 시작
  async analyzeCurrentVideo() {
    const currentVideo = this.detector.getCurrentVideo();
    if (currentVideo && currentVideo.videoId) {
      await this.startAnalysis(currentVideo.videoId);
    } else {
      console.warn('[AITUBE] 분석할 비디오 없음');
    }
  }

  // 캐시 정리
  async clearCache() {
    try {
      await this.apiAnalyzer.clearOldCache();
      console.log('[AITUBE] 캐시 정리 완료');
    } catch (error) {
      console.error('[AITUBE] 캐시 정리 실패:', error);
    }
  }

  // 설정 정보 가져오기
  async getSettings() {
    try {
      const settings = await chrome.storage.local.get({
        autoAnalyze: true,
        apiEndpoint: 'http://localhost:8005/api/analyze',
        enableNotifications: true
      });
      
      return {
        autoAnalyze: settings.autoAnalyze || true,
        apiEndpoint: settings.apiEndpoint || 'http://localhost:8005/api/analyze',
        enableNotifications: settings.enableNotifications !== false
      };
    } catch (error) {
      console.error('[AITUBE] 설정 가져오기 실패:', error);
      return this.getDefaultSettings();
    }
  }

  // 기본 설정
  getDefaultSettings() {
    return {
      autoAnalyze: true,
      apiEndpoint: 'http://localhost:8005/api/analyze',
      enableNotifications: true
    };
  }

  // 설정 저장
  async saveSettings(settings) {
    try {
      await chrome.storage.local.set(settings);
      console.log('[AITUBE] 설정 저장 완료:', settings);
    } catch (error) {
      console.error('[AITUBE] 설정 저장 실패:', error);
    }
  }

  // 서버 상태 확인
  async checkServerStatus() {
    try {
      const status = await this.apiAnalyzer.checkServerStatus();
      return status;
    } catch (error) {
      console.error('[AITUBE] 서버 상태 확인 실패:', error);
      return null;
    }
  }

  // 통계 정보 전송
  async sendUsageStats(action, data = {}) {
    try {
      const stats = {
        action,
        timestamp: Date.now(),
        url: window.location.href,
        userAgent: navigator.userAgent,
        ...data
      };
      
      await chrome.runtime.sendMessage({
        type: 'usageStats',
        data: stats
      });
      
    } catch (error) {
      console.error('[AITUBE] 통계 전송 실패:', error);
    }
  }

  // 확장 상태 정보
  getExtensionStatus() {
    return {
      isAnalyzing: this.isAnalyzing,
      currentVideo: this.currentVideo ? {
        videoId: this.detector.getCurrentVideo().videoId,
        title: document.title,
        duration: this.currentVideo.duration
      } : null,
      overlayVisible: this.overlayUI.isShown(),
      detectorActive: this.detector.isShowsMode,
      lastAnalysis: this.overlayUI.getCurrentResult(),
      retryCount: this.retryCount
    };
  }

  // 정리
  cleanup() {
    console.log('[AITUBE] 정리 시작');
    
    this.cancelCurrentAnalysis();
    
    if (this.detector) {
      this.detector.cleanup();
    }
    
    if (this.overlayUI) {
      this.overlayUI.cleanup();
    }
    
    if (this.frameCapture) {
      this.frameCapture.cleanup();
    }
    
    this.currentVideo = null;
    
    console.log('[AITUBE] 정리 완료');
  }
}

// 전역으로 내보내기
window.AIShowsAnalyzer = AIShowsAnalyzer;

// 페이지 로드 시 자동 초기화
(function() {
  console.log('[AITUBE] AI YouTube 쇼츠 분석기 로드');
  
  if (window.aiShowsAnalyzer) {
    console.log('[AITUBE] 기존 객체 정리');
    window.aiShowsAnalyzer.cleanup();
  }
  
  // DOM 준비 대기
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      window.aiShowsAnalyzer = new AIShowsAnalyzer();
      window.aiShowsAnalyzer.init();
    });
  } else {
    window.aiShowsAnalyzer = new AIShowsAnalyzer();
    window.aiShowsAnalyzer.init();
  }
  
  // 개발 모드에서 전역 접근
  if (typeof window !== 'undefined') {
    window.aiShowsAnalyzerDebug = {
      analyzer: () => window.aiShowsAnalyzer,
      detector: () => window.aiShowsAnalyzer.detector,
      overlay: () => window.aiShowsAnalyzer.overlayUI,
      api: () => window.aiShowsAnalyzer.apiAnalyzer
    };
  }
})();