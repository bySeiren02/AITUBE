// Background Service Worker (Manifest V3 Compatible)
let extensionStatus = {
  isActive: false,
  currentVideo: null,
  analysisCount: 0,
  lastAnalysis: null,
  serverConnectionStatus: 'unknown'
};

// 서버 연결 상태 관리
let serverStatus = {
  connected: false,
  lastCheck: null,
  retryCount: 0,
  maxRetries: 3
};

// 에러 로깅 관리
let errorLog = [];

// 초기화
chrome.runtime.onInstalled.addListener(async (details) => {
  console.log('[AITUBE] 확장 설치 완료:', details);
  
  extensionStatus.isActive = true;
  
  // 초기 설정 저장
  try {
    await chrome.storage.local.set({ 
      extensionStatus: extensionStatus,
      autoAnalyze: true,
      enableNotifications: true,
      apiEndpoint: 'http://localhost:8005/api/analyze',
      autoAnalyzeDelay: 2000,
      maxRetryCount: 3
    });
    console.log('[AITUBE] 초기화 완료');
  } catch (error) {
    console.error('[AITUBE] 초기화 실패:', error);
  }
});

// 확장 시작 시
chrome.runtime.onStartup.addListener(async () => {
  console.log('[AITUBE] 확장 시작');
  extensionStatus.isActive = true;
  updateExtensionStatus();
});

// 메시지 처리
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('[AITUBE] 메시지 수신:', message);
  
  // 탭 타입에 따른 처리
  switch (message.type) {
    case 'getStatus':
      handleGetStatus(sender, sendResponse);
      break;
      
    case 'updateSetting':
      handleUpdateSetting(sender, sendResponse);
      break;
      
    case 'updateStatus':
      handleUpdateStatus(sender, sendResponse);
      break;
      
    case 'clearCache':
      handleClearCache(sender, sendResponse);
      break;
      
    case 'checkServer':
      handleCheckServer(sender, sendResponse);
      break;
      
    case 'analysisComplete':
      handleAnalysisComplete(sender, sendResponse);
      break;
      
    case 'usageStats':
      handleUsageStats(sender, sendResponse);
      break;
      
    default:
      console.warn('[AITUBE] 알 수 없는 메시지:', message);
      sendResponse({ success: false, error: '알 수 없는 명령어입니다' });
  }
  
  return true;
});

// 상태 요청 처리 함수들
async function handleGetStatus(sender, sendResponse) {
  try {
    sendResponse({
      success: true,
      status: extensionStatus
    });
  } catch (error) {
    console.error('[AITUBE] 상태 조회 실패:', error);
    sendResponse({ success: false, error: error.message });
  }
}

async function handleUpdateSetting(sender, sendResponse) {
  try {
    const { key, value } = sender.data;
    await chrome.storage.local.set({ [key]: value });
    sendResponse({ success: true });
    
    console.log('[AITUBE] 설정 변경:', key, '=', value);
  } catch (error) {
    console.error('[AITUBE] 설정 변경 실패:', error);
    sendResponse({ success: false, error: error.message });
  }
}

async function handleUpdateStatus(sender, sendResponse) {
  try {
    const { status, video, data } = sender.data;
    
    if (status) {
      extensionStatus.currentVideo = video;
      
      if (data) {
        // 분석 완료 시
        if (status.status === 'completed') {
          extensionStatus.lastAnalysis = data;
          extensionStatus.analysisCount++;
        }
        
        saveExtensionStatus();
      }
    }
    
    sendResponse({ success: true, status: extensionStatus });
  } catch (error) {
    console.error('[AITUBE] 상태 업데이트 실패:', error);
    sendResponse({ success: false, error: error.message });
  }
}

async function handleClearCache(sender, sendResponse) {
  try {
    // content script에 캐시 삭제 요청
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tabs && tabs.length > 0) {
      const tab = tabs[0];
      
      const result = await chrome.tabs.sendMessage(tab.id, {
        type: 'clearCache'
      });
      
      if (result && result.success) {
        sendResponse({ success: true, message: '캐시 정리 완료' });
      } else {
        sendResponse({ success: false, error: '캐시 정리 실패' });
      }
    }
  } catch (error) {
    console.error('[AITUBE] 캐시 정리 실패:', error);
    sendResponse({ success: false, error: error.message });
  }
}

async function handleCheckServer(sender, sendResponse) {
  try {
    const startTime = Date.now();
    
    // API 서버 상태 확인
    const serverStatus = await checkServerHealth();
    
    sendResponse({
      success: true,
      status: extensionStatus,
      server: serverStatus,
      responseTime: Date.now() - startTime
    });
    
    console.log('[AITUBE] 서버 상태 확인 완료');
    updateExtensionStatus();
    
  } catch (error) {
    console.error('[AITUBE] 서버 상태 확인 실패:', error);
    sendResponse({ success: false, error: error.message });
  }
}

async function handleAnalysisComplete(sender, sendResponse) {
  try {
    const { videoId, score } = sender.data;
    
    // 분석 결과 저장
    await chrome.storage.local.set({
      [`analysis_${videoId}`]: {
        videoId: videoId,
        score: score,
        timestamp: Date.now()
      }
    });
    
    sendResponse({
      success: true,
      message: `분석 완료: ${videoId} (점수: ${score})`
    });
    
  } catch (error) {
    console.error('[AITUBE] 분석 완료 처리 실패:', error);
    sendResponse({ success: false, error: error.message });
  }
}

async function handleUsageStats(sender, sendResponse) {
  try {
    const stats = sender.data;
    
    // 통계 데이터 수집
    const usageData = {
      timestamp: Date.now(),
      action: stats.action,
      videoId: stats.videoId,
      details: stats.details || {}
    };
    
    // 기존 데이터 확인
    const result = await chrome.storage.local.get(['usageStats']);
    let existingStats = result.usageStats || [];
    existingStats.push(usageData);
    
    // 최근 100개까지만 유지
    if (existingStats.length > 100) {
      existingStats = existingStats.slice(-100);
    }
    
    await chrome.storage.local.set({ usageStats: existingStats });
    
    console.log('[AITUBE] 통계 정보 수신:', stats.action);
    
    sendResponse({
      success: true,
      message: '통계 정보 전송 완료'
    });
    
  } catch (error) {
    console.error('[AITUBE] 통계 정보 전송 실패:', error);
    sendResponse({ success: false, error: error.message });
  }
}

// 서버 상태 확인
async function checkServerHealth() {
  const startTime = Date.now();
  serverStatus.retryCount = 0;
  
  try {
    // API 엔드포인트 설정
    const result = await chrome.storage.local.get('apiEndpoint');
    const apiEndpoint = result.apiEndpoint || 'http://localhost:8005/api/analyze';
    
    const response = await fetch(`${apiEndpoint}/status`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'X-Client-Info': navigator.userAgent
      }
    });
    
    if (response.ok) {
      serverStatus.connected = true;
      serverStatus.lastCheck = startTime;
      serverStatus.retryCount = 0;
      
      const data = await response.json();
      console.log('[AITUBE] 서버 응답 성공:', apiEndpoint);
      
      return {
        status: 'connected',
        message: '서버 연결됨',
        responseTime: Date.now() - startTime,
        data: data
      };
    } else {
      serverStatus.connected = false;
      serverStatus.retryCount++;
      
      return {
        status: 'disconnected',
        message: `서버 응답 실패 (${serverStatus.retryCount}/${serverStatus.maxRetries})`
      };
    }
  } catch (error) {
    return {
      status: 'error',
      message: `서버 상태 확인 실패: ${error.message}`
    };
  }
}

// 확장 상태 저장
async function saveExtensionStatus() {
  try {
    const statusToSave = {
      ...extensionStatus,
      timestamp: Date.now()
    };
    
    await chrome.storage.local.set({ extensionStatus: statusToSave });
    console.log('[AITUBE] 상태 저장 완료');
  } catch (error) {
    console.error('[AITUBE] 상태 저장 실패:', error);
  }
}

// 상태 업데이트
function updateExtensionStatus() {
  extensionStatus.isActive = true;
  extensionStatus.serverConnectionStatus = serverStatus.connected ? 'connected' : 'disconnected';
  saveExtensionStatus();
}

// 에러 로깅 함수
function logError(category, error, context = '') {
  const errorInfo = {
    timestamp: Date.now(),
    category: category,
    message: error.message,
    context: context,
    userAgent: navigator.userAgent,
    stack: error.stack
  };
  
  errorLog.push(errorInfo);
  
  // 최근 50개 에러만 유지
  if (errorLog.length > 50) {
    errorLog = errorLog.slice(-50);
  }
  
  console.error(`[AITUBE] ${category}:`, errorInfo);
}

// 에러 로그 조회 함수
function getErrorLogs(limit = 10) {
  return errorLog.slice(-limit);
}

// 전역 객체로 내보내기 (필요시 사용)
if (typeof globalThis !== 'undefined') {
  globalThis.AITUBEBackground = {
    extensionStatus,
    serverStatus,
    errorLog,
    checkServerHealth,
    saveExtensionStatus,
    getErrorLogs
  };
}