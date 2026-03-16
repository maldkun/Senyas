let currentSessionId = null;
let sessionPlan = [];
let fslModule = null;
let currentPrediction = { sign: null, confidence: 0 };
let isValidating = false;
let consecutiveCorrectCount = 0;
const REQUIRED_CONSECUTIVE = 5;

// Batch State
let currentBatchIndex = 0;
let batchRanges = [
    { start: 0, end: 3, label: "Challenging Batch 1" }, // 3 signs
    { start: 3, end: 6, label: "Challenging Batch 2" }, // 3 signs
    { start: 6, end: 8, label: "Challenging Batch 3" }, // 2 signs
    { start: 8, end: 10, label: "Moderate Batch 1" },  // 2 signs
    { start: 10, end: 12, label: "Moderate Batch 2" }, // 2 signs
    { start: 12, end: 15, label: "Easy Batch" }        // 3 signs
];
let currentPhase = 'IDLE'; // IDLE, STUDY, PRACTICE
let currentStudyIndex = 0;   // Index within the batch for studying
let currentPracticeIndex = 0; // Global index for practicing

document.addEventListener('DOMContentLoaded', async () => {
    checkUnlockStatus();
});

async function checkUnlockStatus() {
    try {
        const response = await fetch('/api/ai/unlock_status');
        const data = await response.json();

        const loading = document.getElementById('aiLoading');
        const lockedView = document.getElementById('aiLockedView');
        const startView = document.getElementById('aiStartView');

        loading.style.display = 'none';

        if (data.is_unlocked) {
            startView.style.display = 'block';
        } else {
            lockedView.style.display = 'block';
            updateLockedProgress(data.progress);
        }
    } catch (error) {
        console.error("Error checking unlock status:", error);
    }
}

function updateLockedProgress(progress) {
    const sessPct = Math.min(100, (progress.sessions.current / progress.sessions.required) * 100);
    document.getElementById('progressSessionsBar').style.width = `${sessPct}%`;
    document.getElementById('progressSessionsText').innerText = `${progress.sessions.current} / ${progress.sessions.required}`;

    const attPct = Math.min(100, (progress.attempts.current / progress.attempts.required) * 100);
    document.getElementById('progressAttemptsBar').style.width = `${attPct}%`;
    document.getElementById('progressAttemptsText').innerText = `${progress.attempts.current} / ${progress.attempts.required}`;

    const signPct = Math.min(100, (progress.unique_signs.current / progress.unique_signs.required) * 100);
    document.getElementById('progressSignsBar').style.width = `${signPct}%`;
    document.getElementById('progressSignsText').innerText = `${progress.unique_signs.current} / ${progress.unique_signs.required}`;
}

async function startAiSession() {
    try {
        const btn = event.target;
        const originalText = btn.innerHTML;
        btn.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Preparing...';
        btn.disabled = true;

        const response = await fetch('/api/ai/session/start', {
            method: 'POST',
            redirect: 'manual'
        });

        if (response.status === 302) {
            // Redirect to login page
            const location = response.headers.get('Location');
            if (location) {
                window.location.href = location;
            } else {
                window.location.href = '/auth/landingpage';
            }
            return;
        }

        if (!response.ok) {
            const errText = await response.text();
            throw new Error(`Server Error ${response.status}: ${errText}`);
        }

        const data = await response.json();

        currentSessionId = data.session_id;
        sessionPlan = data.plan;

        document.getElementById('aiStartView').style.display = 'none';

        // Initialize FSL Module
        if (!fslModule) {
            fslModule = new FSLModule({ videoWidth: 640, videoHeight: 480 });
            const video = document.getElementById('aiVideo');
            const canvas = document.getElementById('aiCanvas');
            await fslModule.initialize(video, canvas);

            fslModule.onPrediction = (result) => {
                currentPrediction = result;
                updateDetectionUI(result);

                // Sustained-hold validation
                if (currentPhase === 'PRACTICE' && !isValidating) {
                    const signData = sessionPlan[currentPracticeIndex];
                    if (!signData) return;

                    const isCorrect = result.sign === signData.sign;

                    if (isCorrect) {
                        consecutiveCorrectCount++;
                        console.log(`[AI HOLD] ${result.sign}: ${consecutiveCorrectCount}/${REQUIRED_CONSECUTIVE} frames`);

                        if (consecutiveCorrectCount >= REQUIRED_CONSECUTIVE) {
                            console.log(`[AI HOLD] ✓ VALIDATED ${result.sign}`);
                            isValidating = true;
                            consecutiveCorrectCount = 0;
                            validateSign(true);
                        }
                    } else {
                        if (consecutiveCorrectCount > 0) {
                            console.log(`[AI HOLD] Reset - saw ${result.sign} instead of ${signData.sign}`);
                        }
                        consecutiveCorrectCount = 0;
                    }
                }
            };
        }

        // Initialize Batching
        currentBatchIndex = 0;
        startBatch(0);

    } catch (error) {
        console.error("Error starting session:", error);
        alert(`Failed to start session: ${error.message}`);
        // Reset button
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

function startBatch(batchIdx) {
    if (batchIdx >= batchRanges.length) {
        completeSession();
        return;
    }

    currentBatchIndex = batchIdx;
    const batch = batchRanges[batchIdx];

    // Ensure we don't go out of bounds if plan is smaller than expected (safety)
    if (batch.start >= sessionPlan.length) {
        completeSession();
        return;
    }

    console.log(`[AI BATCH] Starting Batch ${batchIdx + 1}: ${batch.label} (Indices ${batch.start}-${batch.end})`);

    // Start Study Phase for this batch
    currentStudyIndex = batch.start; // Reset study index to start of batch
    startStudyPhase();
}

// --- STUDY PHASE ---

let studyCountdownInterval = null;

function startStudyPhase() {
    currentPhase = 'STUDY';
    const batch = batchRanges[currentBatchIndex];

    if (currentStudyIndex >= batch.end || currentStudyIndex >= sessionPlan.length) {
        // Study phase complete for this batch, move to practice
        console.log(`[AI BATCH] Study Phase Complete. Starting Practice Phase.`);
        currentPracticeIndex = batch.start;
        startPracticePhase();
        return;
    }

    const signData = sessionPlan[currentStudyIndex];
    showStudyModal(signData);
}

function showStudyModal(signData) {
    const modal = document.getElementById('studyModal');
    document.getElementById('studySignChar').innerText = signData.sign;
    // Show "Sign X of Batch" or just global number? Global number is better.
    document.getElementById('currentSignNum').innerText = currentStudyIndex + 1;
    document.getElementById('displayStudyTime').innerText = signData.metrics.study_time + 's';
    document.getElementById('displayThreshold').innerText = signData.metrics.threshold + '%';

    const img = document.getElementById('studySignImage');
    img.src = `/static/images/signs/${signData.sign}.jpg`;
    img.onerror = function () {
        this.style.display = 'none';
        this.parentElement.innerHTML = `<div style="font-size: 120px; color: #1E40AF;">${signData.sign}</div>`;
    };

    modal.style.display = 'flex';

    if (studyCountdownInterval) {
        clearInterval(studyCountdownInterval);
        studyCountdownInterval = null;
    }

    let timeLeft = signData.metrics.study_time;
    const timerEl = document.getElementById('countdownTimer');
    timerEl.innerText = timeLeft;

    studyCountdownInterval = setInterval(() => {
        timeLeft -= 1;
        if (timeLeft <= 0) {
            clearInterval(studyCountdownInterval);
            studyCountdownInterval = null;
            modal.style.display = 'none';

            // Move to next sign in STUDY PHASE
            currentStudyIndex++;
            startStudyPhase();
        } else {
            timerEl.innerText = Math.ceil(timeLeft);
        }
    }, 1000);
}


// --- PRACTICE PHASE ---

async function startPracticePhase() {
    currentPhase = 'PRACTICE';
    const batch = batchRanges[currentBatchIndex];

    if (currentPracticeIndex >= batch.end || currentPracticeIndex >= sessionPlan.length) {
        // Practice phase complete for this batch, move to NEXT BATCH
        console.log(`[AI BATCH] Practice Phase Complete. Moving to next batch.`);
        startBatch(currentBatchIndex + 1);
        return;
    }

    loadPracticeSign(currentPracticeIndex);
}

async function loadPracticeSign(index) {
    const signData = sessionPlan[index];

    document.getElementById('aiPracticeView').style.display = 'block';
    document.getElementById('currentSign').innerText = signData.sign;
    document.getElementById('progressBadge').innerText = `${index + 1} / ${sessionPlan.length}`;
    document.getElementById('requiredThreshold').innerText = signData.metrics.threshold;

    // Reset UI
    isValidating = false;
    updateDetectionUI({ sign: null, confidence: 0 });

    // Start camera if needed
    if (fslModule && !fslModule.isRunning) {
        await fslModule.startCapture();
    }
}

function updateDetectionUI(result) {
    const signData = sessionPlan[currentPracticeIndex];
    if (!signData) return;

    const statusIcon = document.getElementById('statusIcon');
    const statusText = document.getElementById('statusText');
    const statusSubtext = document.getElementById('statusSubtext');
    const confidenceText = document.getElementById('confidenceText');
    const confidenceFill = document.getElementById('confidenceFill');

    if (!result.sign) {
        statusIcon.style.background = 'rgba(239,68,68,0.1)';
        statusIcon.style.color = '#EF4444';
        statusIcon.innerHTML = '<i class="fa fa-hand-paper-o"></i>';
        statusText.innerText = 'Position your hand';
        statusSubtext.innerText = 'Show the sign to the camera';
        confidenceText.innerText = '0%';
        confidenceFill.style.width = '0%';
        return;
    }

    const conf = Math.round(result.confidence * 100);
    confidenceText.innerText = `${conf}%`;
    confidenceFill.style.width = `${conf}%`;

    const isCorrect = result.sign === signData.sign;
    const meetsThreshold = conf >= signData.metrics.threshold;

    if (isCorrect && meetsThreshold) {
        statusIcon.style.background = 'rgba(16,185,129,0.1)';
        statusIcon.style.color = '#10B981';
        statusIcon.innerHTML = '<i class="fa fa-check"></i>';
        statusText.innerText = 'Perfect!';
        statusSubtext.innerText = `Detected: ${result.sign} (${conf}%)`;
    } else if (isCorrect && !meetsThreshold) {
        statusIcon.style.background = 'rgba(245,158,11,0.1)';
        statusIcon.style.color = '#F59E0B';
        statusIcon.innerHTML = '<i class="fa fa-thumbs-up"></i>';
        statusText.innerText = 'Good, hold steady!';
        statusSubtext.innerText = `Need ${signData.metrics.threshold}%, current: ${conf}%`;
    } else {
        statusIcon.style.background = 'rgba(239,68,68,0.1)';
        statusIcon.style.color = '#EF4444';
        statusIcon.innerHTML = '<i class="fa fa-times"></i>';
        statusText.innerText = `Detected: ${result.sign}`;
        statusSubtext.innerText = `Expected: ${signData.sign}`;
    }
}

async function autoValidateIfReady() {
    // Deprecated? No, potentially still used by manual trigger if we had one?
    // But we are using the sustained hold logic in onPrediction now.
    // Keeping this as a potential helper or for debug if needed.
    return;
}

async function validateSign(isCorrect) {
    const signData = sessionPlan[currentPracticeIndex];

    console.log(`[AI VALIDATE] Sign: ${signData.sign}, Detected: ${currentPrediction.sign}, Conf: ${(currentPrediction.confidence * 100).toFixed(1)}%, Threshold: ${signData.metrics.threshold}%`);

    const payload = {
        session_id: currentSessionId,
        sign_id: signData.sign,
        detected_sign: currentPrediction.sign || '',
        confidence: (currentPrediction.confidence || 0) * 100,
        threshold: signData.metrics.threshold,
        study_time: signData.metrics.study_time
    };

    try {
        const response = await fetch('/api/ai/session/validate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const result = await response.json();
        console.log(`[AI VALIDATE] Server response: is_correct=${result.is_correct}`);

        // Stop camera briefly? No, keep it running for smoothness, but maybe pause UI updates?
        // Actually, we hide the view so stopping capture is good for PERF and clarity.
        if (fslModule && fslModule.isRunning) {
            fslModule.stopCapture();
        }

        document.getElementById('aiPracticeView').style.display = 'none';

        // Proceed to next sign in PRACTICE PHASE
        setTimeout(() => {
            currentPracticeIndex++;
            startPracticePhase();
        }, 300);

    } catch (error) {
        console.error("Validation error:", error);
        isValidating = false;
    }
}

async function skipSign() {
    if (isValidating) return;
    isValidating = true;

    const signData = sessionPlan[currentPracticeIndex];

    // Log as incorrect
    const payload = {
        session_id: currentSessionId,
        sign_id: signData.sign,
        detected_sign: 'SKIPPED',
        confidence: 0,
        threshold: signData.metrics.threshold,
        study_time: signData.metrics.study_time
    };

    try {
        await fetch('/api/ai/session/validate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (fslModule && fslModule.isRunning) {
            fslModule.stopCapture();
        }

        document.getElementById('aiPracticeView').style.display = 'none';

        // Proceed to next sign in PRACTICE PHASE
        setTimeout(() => {
            currentPracticeIndex++;
            startPracticePhase();
        }, 300);

    } catch (error) {
        console.error("Skip error:", error);
        isValidating = false;
    }
}

async function completeSession() {
    console.log('[AI COMPLETE] Session completing...');

    if (fslModule && fslModule.isRunning) {
        fslModule.stopCapture();
    }

    // Build tier map from session plan
    const tierMap = {};
    sessionPlan.forEach(item => {
        tierMap[item.sign] = item.metrics.difficulty_label;
    });

    try {
        const response = await fetch('/api/ai/session/complete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: currentSessionId,
                tier_map: tierMap
            })
        });

        if (!response.ok) {
            const errorText = await response.text();
            alert(`Failed to complete session: ${errorText}`);
            return;
        }

        const report = await response.json();

        document.getElementById('aiReportView').style.display = 'block';
        document.getElementById('reportCorrect').innerText = report.total_correct;
        document.getElementById('reportTotal').innerText = report.total_signs;

        // Populate breakdown tables
        populateSignTable('challengingTableBody', report.session_breakdown.challenging);
        populateSignTable('moderateTableBody', report.session_breakdown.moderate);
        populateSignTable('easyTableBody', report.session_breakdown.easy);

    } catch (error) {
        console.error("[AI COMPLETE] Completion error:", error);
        alert(`Error completing session: ${error.message}`);
    }
}

function populateSignTable(tableId, signs) {
    const tbody = document.getElementById(tableId);
    tbody.innerHTML = '';

    if (!signs || signs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No signs in this category</td></tr>';
        return;
    }

    signs.forEach(sign => {
        const row = document.createElement('tr');
        const resultBadge = sign.was_correct
            ? '<span class="badge badge-success">✓ Correct</span>'
            : '<span class="badge badge-danger">✗ Incorrect</span>';

        row.innerHTML = `
            <td><strong>${sign.sign}</strong></td>
            <td>${resultBadge}</td>
            <td>${sign.accuracy}</td>
            <td>${sign.confidence}</td>
            <td>${sign.total_attempts}</td>
            <td>${sign.predicted_success}</td>
        `;
        tbody.appendChild(row);
    });
}

