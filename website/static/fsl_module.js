/**
 * Filipino Sign Language (FSL) Recognition Module
 * Handles real-time hand landmark extraction, sign prediction, and progressive learning
 * 
 * Usage:
 *   const fslModule = new FSLModule();
 *   await fslModule.initialize();
 *   fslModule.startCapture();
 *   fslModule.onPrediction = (result) => console.log(result);
 */

class FSLModule {
    constructor(config = {}) {
        this.config = {
            videoWidth: config.videoWidth || 480,
            videoHeight: config.videoHeight || 360,
            minDetectionConfidence: config.minDetectionConfidence || 0.5,
            minTrackingConfidence: config.minTrackingConfidence || 0.4,
            predictionSmoothWindow: config.predictionSmoothWindow || 3,
            apiBaseUrl: config.apiBaseUrl || '/api/fsl',
            ...config
        };

        this.hands = null;
        this.camera = null;
        this.video = null;
        this.canvas = null;
        this.stream = null;
        this.isRunning = false;

        // Callbacks
        this.onPrediction = null;
        this.onSequenceProgress = null;
        this.onHandDetected = null;
        this.onError = null;

        // State
        this.currentSession = null;
        this.predictionBuffer = [];
        this.isPredicting = false;
        this.lastPredictionTime = 0;
    }

    async initialize(videoElement, canvasElement) {
        /**
         * Initialize FSL module with video and canvas elements
         */
        try {
            this.video = videoElement;
            this.canvas = canvasElement;

            // Set canvas dimensions
            this.canvas.width = this.config.videoWidth;
            this.canvas.height = this.config.videoHeight;

            // Set video dimensions
            this.video.width = this.config.videoWidth;
            this.video.height = this.config.videoHeight;

            // Create offscreen canvas for low-res processing
            this.processCanvas = document.createElement('canvas');
            this.processCanvas.width = 320;
            this.processCanvas.height = 240;

            // Initialize MediaPipe Hands
            this.hands = new Hands({
                locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`
            });

            this.hands.setOptions({
                maxNumHands: 1,
                modelComplexity: this.config.modelComplexity || 1, // Default to Full model (1) for better accuracy
                minDetectionConfidence: this.config.minDetectionConfidence,
                minTrackingConfidence: this.config.minTrackingConfidence
            });

            this.hands.onResults(this.onHandsResults.bind(this));

            // Wait for MediaPipe to be ready
            await new Promise((resolve) => {
                const checkReady = () => {
                    if (this.hands && typeof this.hands.send === 'function') {
                        resolve();
                    } else {
                        setTimeout(checkReady, 100);
                    }
                };
                checkReady();
            });

            console.log("✅ FSL Module initialized (Lite Mode)");
            return true;
        } catch (error) {
            console.error("❌ Failed to initialize FSL module:", error);
            if (this.onError) this.onError(error);
            return false;
        }
    }

    async startCapture() {
        /**
         * Start capturing from webcam
         */
        try {
            console.log("Starting camera capture...");

            if (this.stream) {
                this.stopCapture();
            }

            this.stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: this.config.videoWidth,
                    height: this.config.videoHeight,
                    facingMode: 'user'
                }
            });

            console.log("Camera stream acquired");

            this.video.srcObject = this.stream;

            // Wait for video to be ready
            await new Promise((resolve) => {
                const onReady = () => {
                    if (this.video.readyState >= 2) {
                        this.video.removeEventListener('loadedmetadata', onReady);
                        resolve();
                    }
                };
                this.video.addEventListener('loadedmetadata', onReady);
                setTimeout(resolve, 2000);
            });

            console.log("Video ready, starting frame loop");

            // Explicitly play video
            try {
                await this.video.play();
            } catch (err) {
                console.error("Error playing video:", err);
            }

            this.isRunning = true;
            this.lastResults = null;

            // Rendering Loop (High FPS for smooth video)
            const renderLoop = () => {
                if (!this.isRunning) return;

                const canvasCtx = this.canvas.getContext('2d');
                canvasCtx.save();
                canvasCtx.clearRect(0, 0, this.canvas.width, this.canvas.height);

                // Draw video feed
                if (this.video.readyState >= 2) {
                    canvasCtx.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);
                }

                // Draw landmarks overlay
                if (this.lastResults && this.lastResults.multiHandLandmarks && this.lastResults.multiHandLandmarks.length > 0) {
                    const landmarks = this.lastResults.multiHandLandmarks[0];
                    this.drawHandSkeleton(canvasCtx, landmarks);
                }

                canvasCtx.restore();
                requestAnimationFrame(renderLoop);
            };
            requestAnimationFrame(renderLoop);

            // Processing Loop (Throttled)
            let lastProcessTime = 0;
            const processLoop = async () => {
                if (!this.isRunning || !this.hands) return;

                const now = Date.now();
                // Process at 5 FPS (200ms) for stability
                if (now - lastProcessTime >= 200) {
                    try {
                        if (this.video.readyState >= 2) {
                            const processCtx = this.processCanvas.getContext('2d');
                            processCtx.drawImage(this.video, 0, 0, this.processCanvas.width, this.processCanvas.height);

                            await this.hands.send({ image: this.processCanvas });
                            lastProcessTime = now;
                        }
                    } catch (e) {
                        console.error("Processing error:", e);
                    }
                }

                setTimeout(processLoop, 100);
            };
            processLoop();

            console.log("✅ Camera capture started (Lite Mode)");
        } catch (error) {
            console.error("❌ Camera access error:", error);
            if (this.onError) this.onError(error);
        }
    }

    stopCapture() {
        this.isRunning = false;
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        if (this.video) {
            this.video.srcObject = null;
        }
        console.log("✅ Camera capture stopped");
    }

    onHandsResults(results) {
        if (!this._hasReceivedResults) {
            console.log("✅ First MediaPipe result received!");
            this._hasReceivedResults = true;
        }

        this.lastResults = results;

        if (results.multiHandLandmarks && results.multiHandLandmarks.length > 0) {
            const landmarks = results.multiHandLandmarks[0];

            // console.log("👋 Hand detected! Landmarks count:", landmarks.landmark.length);

            if (this.onHandDetected) {
                this.onHandDetected(true);
            }

            const landmarkVector = this.extractLandmarkVector(landmarks);

            const now = Date.now();
            if ((!this.lastPredictionTime || (now - this.lastPredictionTime > 200)) && !this.isPredicting) {
                console.log("🔮 Sending prediction request...");
                this.predict(landmarkVector);
                this.lastPredictionTime = now;
            }
        } else {
            if (this.onHandDetected) {
                this.onHandDetected(false);
            }
            this.predictionBuffer = [];
        }
    }

    extractLandmarkVector(landmarks) {
        const vector = [];
        // MediaPipe returns landmarks as an array directly, not landmarks.landmark
        const landmarkArray = landmarks.landmark || landmarks;

        // Handle both array and object with numeric keys
        if (Array.isArray(landmarkArray)) {
            for (let landmark of landmarkArray) {
                vector.push(landmark.x, landmark.y, landmark.z);
            }
        } else {
            // If it's an object with numeric keys (0, 1, 2, ...)
            for (let i = 0; i < 21; i++) {
                if (landmarkArray[i]) {
                    vector.push(landmarkArray[i].x, landmarkArray[i].y, landmarkArray[i].z);
                }
            }
        }

        console.log("📊 Extracted landmark vector, length:", vector.length);
        return vector;
    }

    drawHandSkeleton(ctx, landmarks) {
        const h = this.canvas.height;
        const w = this.canvas.width;

        // Get the actual landmark array
        const landmarkArray = landmarks.landmark || landmarks;

        // Draw landmarks
        ctx.fillStyle = '#FF0000';
        if (Array.isArray(landmarkArray)) {
            for (let landmark of landmarkArray) {
                const x = landmark.x * w;
                const y = landmark.y * h;
                ctx.beginPath();
                ctx.arc(x, y, 5, 0, 2 * Math.PI);
                ctx.fill();
            }
        } else {
            for (let i = 0; i < 21; i++) {
                if (landmarkArray[i]) {
                    const x = landmarkArray[i].x * w;
                    const y = landmarkArray[i].y * h;
                    ctx.beginPath();
                    ctx.arc(x, y, 5, 0, 2 * Math.PI);
                    ctx.fill();
                }
            }
        }

        // Draw connections
        const connections = [
            [0, 1], [1, 2], [2, 3], [3, 4],
            [0, 5], [5, 6], [6, 7], [7, 8],
            [0, 9], [9, 10], [10, 11], [11, 12],
            [0, 13], [13, 14], [14, 15], [15, 16],
            [0, 17], [17, 18], [18, 19], [19, 20],
            [5, 9], [9, 13], [13, 17]
        ];

        ctx.strokeStyle = '#00FF00';
        ctx.lineWidth = 2;

        for (const [startIdx, endIdx] of connections) {
            const start = landmarkArray[startIdx];
            const end = landmarkArray[endIdx];

            if (start && end) {
                ctx.beginPath();
                ctx.moveTo(start.x * w, start.y * h);
                ctx.lineTo(end.x * w, end.y * h);
                ctx.stroke();
            }
        }
    }

    async predict(landmarkVector) {
        if (this.abortController) {
            this.abortController.abort();
        }

        this.abortController = new AbortController();
        const signal = this.abortController.signal;

        try {
            this.isPredicting = true;
            const response = await fetch(`${this.config.apiBaseUrl}/predict`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    landmarks: landmarkVector,
                    session_id: this.currentSession,
                    smooth: true
                }),
                signal: signal
            });

            if (!response.ok) {
                throw new Error(`Prediction failed: ${response.status}`);
            }

            const result = await response.json();

            if (result.sign) {
                this.predictionBuffer.push(result.sign);
                if (this.predictionBuffer.length > this.config.predictionSmoothWindow) {
                    this.predictionBuffer.shift();
                }
            } else {
                this.predictionBuffer = [];
            }

            if (this.onPrediction) {
                this.onPrediction(result);
            }
        } catch (error) {
            if (error.name === 'AbortError') return;

            console.error("Prediction error:", error);
            if (this.onPrediction) {
                this.onPrediction({
                    sign: null,
                    confidence: 0,
                    threshold_met: false,
                    error: true
                });
            }
        } finally {
            this.isPredicting = false;
        }
    }

    async startSequence(signs) {
        try {
            const response = await fetch(`${this.config.apiBaseUrl}/sequence/start`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ signs })
            });

            if (!response.ok) {
                throw new Error(`Failed to start sequence: ${response.status}`);
            }

            const result = await response.json();
            this.currentSession = result.session_id;

            console.log("✅ Sequence started:", result);
            return result;
        } catch (error) {
            console.error("Error starting sequence:", error);
            if (this.onError) this.onError(error);
            return null;
        }
    }

    async startSequenceByPart(partIdx) {
        try {
            const response = await fetch(`${this.config.apiBaseUrl}/sequence/start`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ part: partIdx })
            });

            if (!response.ok) {
                throw new Error(`Failed to start part sequence: ${response.status}`);
            }

            const result = await response.json();
            this.currentSession = result.session_id;

            console.log(`✅ Part ${partIdx} sequence started:`, result);
            return result;
        } catch (error) {
            console.error("Error starting part sequence:", error);
            if (this.onError) this.onError(error);
            return null;
        }
    }

    async checkSign(detectedSign, confidence) {
        try {
            const response = await fetch(`${this.config.apiBaseUrl}/sequence/check`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    sign: detectedSign,
                    confidence: confidence,
                    session_id: this.currentSession
                })
            });

            if (!response.ok) {
                throw new Error(`Check failed: ${response.status}`);
            }

            const result = await response.json();

            if (this.onSequenceProgress) {
                this.onSequenceProgress(result);
            }

            return result;
        } catch (error) {
            console.error("Error checking sign:", error);
            if (this.onError) this.onError(error);
            return null;
        }
    }

    async checkSignWithPart(detectedSign, confidence, partIdx) {
        try {
            const response = await fetch(`${this.config.apiBaseUrl}/sequence/check`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    sign: detectedSign,
                    confidence: confidence,
                    session_id: this.currentSession,
                    part: partIdx
                })
            });

            if (!response.ok) {
                throw new Error(`Check with part failed: ${response.status}`);
            }

            const result = await response.json();

            if (this.onSequenceProgress) {
                this.onSequenceProgress(result);
            }

            return result;
        } catch (error) {
            console.error("Error checking sign with part:", error);
            if (this.onError) this.onError(error);
            return null;
        }
    }

    async getProgress() {
        try {
            const response = await fetch(`${this.config.apiBaseUrl}/sequence/progress?session_id=${this.currentSession}`);

            if (!response.ok) {
                throw new Error(`Get progress failed: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error("Error getting progress:", error);
            if (this.onError) this.onError(error);
            return null;
        }
    }

    async getAvailableSigns() {
        try {
            const response = await fetch(`${this.config.apiBaseUrl}/available-signs`);

            if (!response.ok) {
                throw new Error(`Get signs failed: ${response.status}`);
            }

            const result = await response.json();
            return result.signs;
        } catch (error) {
            console.error("Error getting available signs:", error);
            if (this.onError) this.onError(error);
            return [];
        }
    }
}


// Export for use in HTML
if (typeof window !== 'undefined') {
    window.FSLModule = FSLModule;
}
