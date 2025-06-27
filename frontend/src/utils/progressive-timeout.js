// frontend/src/utils/progressive-timeout.js
export const TIMEOUT_STAGES = {
    WARNING_1: 15 * 1000,  // 15秒
    WARNING_2: 30 * 1000,  // 30秒  
    WARNING_3: 45 * 1000,  // 45秒
    TIMEOUT: 60 * 1000,    // 60秒
  };
  
  export const TIMEOUT_MESSAGES = {
    WARNING_1: "処理中です...⏳",
    WARNING_2: "もう少しお待ちください...🕐", 
    WARNING_3: "サーバーが混雑しているようです...🌐",
    TIMEOUT: "申し訳ございません。処理に時間がかかりすぎています。もう一度お試しください。🙏"
  };
  
  export class ProgressiveTimeoutManager {
    constructor(onStatusUpdate) {
      this.onStatusUpdate = onStatusUpdate;
      this.timers = [];
      this.isActive = false;
    }
  
    start(taskName = 'タスク') {
      this.cleanup(); // 既存のタイマーをクリア
      this.isActive = true;
  
      // 15秒後: 処理中です...
      this.timers.push(setTimeout(() => {
        if (this.isActive) {
          this.onStatusUpdate(TIMEOUT_MESSAGES.WARNING_1);
        }
      }, TIMEOUT_STAGES.WARNING_1));
  
      // 30秒後: もう少しお待ちください...
      this.timers.push(setTimeout(() => {
        if (this.isActive) {
          this.onStatusUpdate(TIMEOUT_MESSAGES.WARNING_2);
        }
      }, TIMEOUT_STAGES.WARNING_2));
  
      // 45秒後: サーバーが混雑しているようです...
      this.timers.push(setTimeout(() => {
        if (this.isActive) {
          this.onStatusUpdate(TIMEOUT_MESSAGES.WARNING_3);
        }
      }, TIMEOUT_STAGES.WARNING_3));
  
      // 60秒後: タイムアウトエラー
      this.timers.push(setTimeout(() => {
        if (this.isActive) {
          this.onStatusUpdate(TIMEOUT_MESSAGES.TIMEOUT);
          this.onTimeout();
        }
      }, TIMEOUT_STAGES.TIMEOUT));
    }
  
    stop() {
      this.isActive = false;
      this.cleanup();
    }
  
    cleanup() {
      this.timers.forEach(timer => clearTimeout(timer));
      this.timers = [];
    }
  
    onTimeout() {
      // タイムアウト時の追加処理があればここに
      console.warn('[TIMEOUT] 処理がタイムアウトしました');
    }
  }
  
  // チャット専用の軽量版
  export class ChatTimeoutManager {
    constructor(onStatusUpdate) {
      this.onStatusUpdate = onStatusUpdate;
      this.timer = null;
    }
  
    start() {
      this.cleanup();
      
      // チャットは15秒でタイムアウト
      this.timer = setTimeout(() => {
        this.onStatusUpdate("チャット処理に時間がかかっています。もう一度お試しください。💬");
      }, 15 * 1000);
    }
  
    stop() {
      this.cleanup();
    }
  
    cleanup() {
      if (this.timer) {
        clearTimeout(this.timer);
        this.timer = null;
      }
    }
  }
  
  // 画像生成専用（より長いタイムアウト）
  export class ImageTimeoutManager {
    constructor(onStatusUpdate) {
      this.onStatusUpdate = onStatusUpdate;
      this.timers = [];
      this.isActive = false;
    }
  
    start(stepIndex = 0) {
      this.cleanup();
      this.isActive = true;
  
      // 20秒後
      this.timers.push(setTimeout(() => {
        if (this.isActive) {
          this.onStatusUpdate(`画像生成中です...🎨 (${stepIndex + 1}番目の手順)`);
        }
      }, 20 * 1000));
  
      // 40秒後
      this.timers.push(setTimeout(() => {
        if (this.isActive) {
          this.onStatusUpdate(`画像生成に時間がかかっています...⏳ (${stepIndex + 1}番目の手順)`);
        }
      }, 40 * 1000));
  
      // 60秒後
      this.timers.push(setTimeout(() => {
        if (this.isActive) {
          this.onStatusUpdate(`サーバーが混雑しているようです...🌐 (${stepIndex + 1}番目の手順)`);
        }
      }, 60 * 1000));
  
      // 90秒後: タイムアウト
      this.timers.push(setTimeout(() => {
        if (this.isActive) {
          this.onStatusUpdate(`画像生成がタイムアウトしました。次の手順に進みます...⏭️`);
        }
      }, 90 * 1000));
    }
  
    stop() {
      this.isActive = false;
      this.cleanup();
    }
  
    cleanup() {
      this.timers.forEach(timer => clearTimeout(timer));
      this.timers = [];
    }
  }