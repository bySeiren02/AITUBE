// popup 스크립트
document.addEventListener('DOMContentLoaded', function() {
  initializePopup();
});

// 초기화
async function initializePopup() {
  try {
    console.log('[AITUBE Popup] 팝업');
    
    // 설정 로드
    await loadSettings();
    
    // 상태 업데이트
    updateExtensionStatus();
    
    // 이벤트 리스너 설정
    setupEventListeners();
    
    // Chrome 스토리지 API 연결 설정
    if (chrome && chrome.runtime) {
      setupChromeAPIs();
    }
    
  } catch (error) {
    console.error('[AITUBE] 초기화 실패:', error);
  }
}

// 설정 로드
async function loadSettings() {
  try {
    const settings = await chrome.storage.local.get({
      autoAnalyze: true,
      enableNotifications: true,
      apiEndpoint: 'http://localhost:8005/api/analyze',
      autoAnalyzeDelay: 2000,
      maxRetryCount: 3
    });
    
    updateUI(settings);
  } catch (error) {
    console.error('[AITUBE] 설정 로드 실패:', error);
  }
}

// 설정 UI 업데이트
function updateUI(settings) {
  const autoAnalyze = document.getElementById('auto-analyze');
  const enableNotifications = document.getElementById('enable-notifications');
  const apiEndpoint = document.getElementById('api-endpoint');
  
  if (autoAnalyze) {
    autoAnalyze.checked = settings.autoAnalyze !== false;
  }
  
  if (enableNotifications) {
    enableNotifications.checked = settings.enableNotifications !== false;
  }
  
  if (apiEndpoint) {
    apiEndpoint.value = settings.apiEndpoint || 'http://localhost:8005/api/analyze';
  }
}

// 확장 상태 업데이트
async function updateExtensionStatus() {
  try {
    // content script에 상태 요청
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    
    if (tabs && tabs.length > 0) {
      const tab = tabs[0];
      
      // content script에 메시지 전송
      chrome.tabs.sendMessage(tab.id, {
        type: 'getStatus'
      }, (response) => {
        if (response && response.status) {
          updateStatusDisplay(response.status);
          updateServerStatus(response.status);
          updateCacheCount(response.cacheCount);
        }
      });
    }
    
  } catch (error) {
    console.error('[AITUBE] 상태 업데이트 실패:', error);
  }
}

// 상태 표시 업데이트
function updateStatusDisplay(status) {
  const statusElement = document.getElementById('analysis-status');
  if (statusElement) {
    statusElement.className = 'status-value status-' + (status.status || 'bad');
    statusElement.textContent = status.message || '알 수 없음';
  }
}

// 서버 상태 업데이트
function updateServerStatus(status) {
  const serverElement = document.getElementById('server-status');
  if (serverElement) {
    serverElement.className = 'status-value status-' + (status.status || 'bad');
    serverElement.textContent = status.message || '연결 안됨';
  }
}

// 캐시 수 업데이트
function updateCacheCount(count) {
  const cacheElement = document.getElementById('cached-count');
  if (cacheElement) {
    cacheElement.textContent = count || '0';
  }
}

// 마지막 분석 정보 업데이트
function updateLastAnalysis(analysis) {
  const lastElement = document.getElementById('last-analysis');
  if (lastElement && analysis) {
    const time = analysis.timestamp ? new Date(analysis.timestamp).toLocaleString() : '시간 기록 없음';
    lastElement.textContent = `${analysis.score}점 - ${time}`;
  }
}

// 이벤트 리스너 설정
function setupEventListeners() {
  // 자동 분석 토글
  const autoAnalyze = document.getElementById('auto-analyze');
  if (autoAnalyze) {
    autoAnalyze.addEventListener('change', async (e) => {
      const checked = e.target.checked;
      await saveSettings({ autoAnalyze: checked });
      
      // content script에 변경 통지
      const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
      if (tabs && tabs.length > 0) {
        chrome.tabs.sendMessage(tabs[0].id, {
          type: 'updateSetting',
          data: { autoAnalyze: checked }
        });
      }
    });
  }
  
  // 분석 알림 토글
  const enableNotifications = document.getElementById('enable-notifications');
  if (enableNotifications) {
    enableNotifications.addEventListener('change', async (e) => {
      const checked = e.target.checked;
      await saveSettings({ enableNotifications: checked });
    });
  }
  
  // API 엔드포인트
  const apiEndpoint = document.getElementById('api-endpoint');
  if (apiEndpoint) {
    apiEndpoint.addEventListener('blur', async (e) => {
      const value = e.target.value.trim();
      if (value) {
        await saveSettings({ apiEndpoint: value });
        
        // 유효성 검증
        if (isValidUrl(value)) {
          updateUI({ apiEndpoint: value });
        } else {
          showNotification('유효하지 않은 API 엔드포인트입니다', 'error');
        apiEndpoint.value = '';
          updateUI({ apiEndpoint: '' });
        }
      }
    });
  }
  
  // 캐시 정리 버튼
  document.getElementById('clear-cache').addEventListener('click', async () => {
    try {
      const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
      if (tabs && tabs.length > 0) {
        const result = await chrome.tabs.sendMessage(tabs[0].id, {
          type: 'clearCache'
        });
        
        if (result && result.success) {
          showNotification('캐시가 정리되었습니다');
          updateCacheCount(0);
        }
      }
    } catch (error) {
      showNotification('캐시 정리 실패: ' + error.message, 'error');
    }
  });
  
  // 서버 상태 확인 버튼
  document.getElementById('check-server').addEventListener('click', async () => {
    try {
      const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
      if (tabs && tabs.length > 0) {
        const result = await chrome.tabs.sendMessage(tabs[0].id, {
          type: 'checkServer'
        });
        
        if (result && result.status) {
          updateServerStatus(result.status);
          showNotification('서버 상태: ' + result.status.message, result.status.status);
        } else {
          showNotification('서버 상태 확인 실패', 'error');
        }
      }
    } catch (error) {
      showNotification('서버 상태 확인 실패: ' + error.message, 'error');
    }
  });
  
  // 기본 설정 복귀 버튼
  document.getElementById('reset-settings').addEventListener('click', async () => {
    try {
      await saveSettings(getDefaultSettings());
      showNotification('기본 설정으로 복귀되었습니다');
      updateUI(getDefaultSettings());
    } catch (error) {
      showNotification('설정 복귀 실패: ' + error.message, 'error');
    }
  });
}

// Chrome 스토리지 API 설정
async function setupChromeAPIs() {
  // 확장 활성화 상태 확인
  try {
    const response = await chrome.runtime.sendMessage({ type: 'checkActive' });
    console.log('[AITUBE] 확장 활성 상태:', response.active);
  } catch (error) {
    console.error('[AITUBE] Chrome API 연결 실패:', error);
  }
}

// 설정 저장
async function saveSettings(settings) {
  try {
    await chrome.storage.local.set(settings);
    console.log('[AITUBE] 설정 저장:', settings);
  } catch (error) {
    console.error('[AITUBE] 설정 저장 실패:', error);
  }
}

// 기본 설정
function getDefaultSettings() {
  return {
    autoAnalyze: true,
    enableNotifications: true,
    apiEndpoint: 'http://localhost:8005/api/analyze',
    autoAnalyzeDelay: 2000,
    maxRetryCount: 3
  };
}

// 알림 표시
function showNotification(message, type = 'info') {
  if (!Notification.permission) {
    console.log('[AITUBE] 알림 (권한 없음):', message);
    return;
  }
  
  // Chrome 알림 권한 확인
  const notificationOptions = {
    type: type,
    iconUrl: chrome.runtime.getURL('icon128.png'),
    message: message
  };
  
  chrome.notifications.create(notificationOptions);
}

// URL 유효성 검증
function isValidUrl(url) {
  try {
    const urlObj = new URL(url);
    return urlObj.protocol === 'https:' || urlObj.protocol === 'http:';
  } catch {
    return false;
  }
}