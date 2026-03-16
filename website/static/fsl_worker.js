/**
 * Web Worker for FSL MediaPipe Processing
 * Handles heavy image processing off the main thread
 */

// Import MediaPipe Hands and Camera Utils
importScripts('https://cdn.jsdelivr.net/npm/@mediapipe/hands/hands.js');

let hands = null;

// Initialize MediaPipe Hands
const initializeHands = (config) => {
    hands = new Hands({
        locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`
    });

    hands.setOptions({
        maxNumHands: 1,
        modelComplexity: 0, // Lite model for faster CPU inference in Worker
        minDetectionConfidence: config.minDetectionConfidence || 0.7,
        minTrackingConfidence: config.minTrackingConfidence || 0.5
    });

    hands.onResults((results) => {
        // Post results back to main thread
        // We only send the landmarks, not the image to save bandwidth
        const simpleResults = {
            multiHandLandmarks: results.multiHandLandmarks,
            multiHandedness: results.multiHandedness
        };
        postMessage({ type: 'results', results: simpleResults });
    });

    console.log("Worker: MediaPipe Hands initialized");
    postMessage({ type: 'initialized' });
};

// Handle messages from main thread
onmessage = async (e) => {
    const { type, payload, config } = e.data;

    if (type === 'initialize') {
        try {
            console.log("Worker: Initializing hands...");
            initializeHands(config);
        } catch (error) {
            postMessage({ type: 'error', error: error.message });
        }
    } else if (type === 'process') {
        if (!hands) {
            // console.log("Worker waiting for hands...");
            return;
        }
        try {
            // payload is ImageData
            await hands.send({ image: payload });
            // ImageData doesn't need closing
        } catch (error) {
            console.error("Worker processing error:", error);
        }
    }
};
