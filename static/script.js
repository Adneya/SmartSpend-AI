function addExpense(){

    let amount = document.getElementById("amount").value
    
    let currentBalance = document.getElementById("balance").innerText.replace("₹","")
    
    currentBalance = parseInt(currentBalance)
    
    let newBalance = currentBalance - amount
    
    document.getElementById("balance").innerText = "₹"+newBalance
    
}

// OCR Functions
function submitOCR() {
    const fileInput = document.getElementById("ocrInput");
    const file = fileInput.files[0];
    
    if (!file) {
        showOCRError("Please select an image file");
        return;
    }
    
    // Hide previous results and show loading
    hideOCRResults();
    hideOCRError();
    document.getElementById("ocrLoading").style.display = "block";
    
    // Create FormData for file upload
    const formData = new FormData();
    formData.append("file", file);
    
    // Send to backend
    fetch("/api/ocr", {
        method: "POST",
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        document.getElementById("ocrLoading").style.display = "none";
        
        if (data.error) {
            showOCRError(data.error);
        } else {
            displayOCRResults(data);
        }
    })
    .catch(error => {
        document.getElementById("ocrLoading").style.display = "none";
        showOCRError("Error: " + error.message);
    });
}

function displayOCRResults(data) {
    const resultsDiv = document.getElementById("ocrResults");
    const extractedTextDiv = document.getElementById("extractedText");
    
    // Display the extracted text
    extractedTextDiv.innerHTML = "<p>" + data.extracted_text.replace(/\n/g, "<br>") + "</p>";
    
    // Store data for later use
    window.lastOCRData = data;
    
    // Show results
    resultsDiv.style.display = "block";
}

function addFromOCR() {
    if (!window.lastOCRData) {
        showOCRError("No OCR data available");
        return;
    }
    
    const texto = window.lastOCRData.extracted_text;
    
    // Try to extract amount from text using regex (looks for currency amounts)
    const amountMatch = texto.match(/₹\s*([\d,]+\.?\d*)|(\d+\.?\d*)\s*₹/);
    const amount = amountMatch ? amountMatch[1] || amountMatch[2] : "0";
    
    // Update balance
    let currentBalance = document.getElementById("balance").innerText.replace("₹","").replace(/,/g, "");
    currentBalance = parseInt(currentBalance);
    let newBalance = currentBalance - parseFloat(amount);
    document.getElementById("balance").innerText = "₹" + newBalance.toLocaleString();
    
    // Alert user
    alert("Expense of ₹" + amount + " added from receipt!");
}

function hideOCRResults() {
    document.getElementById("ocrResults").style.display = "none";
}

function hideOCRError() {
    document.getElementById("ocrError").style.display = "none";
}

function showOCRError(message) {
    const errorDiv = document.getElementById("ocrError");
    errorDiv.innerHTML = "<p>" + message + "</p>";
    errorDiv.style.display = "block";
}

// Camera Variables
let cameraStream = null;
let cameraActive = false;
let capturedBlob = null;  // Store the captured image blob

// DroidCam Variables
let droidcamConnected = false;
let droidcamIp = null;
let droidcamPort = 4747;
let droidcamRefreshInterval = null;
let droidcamCapturedBlob = null;

// Switch between OCR tabs (Upload vs Camera)
function switchOCRTab(tab) {
    // Hide all tabs
    document.getElementById("uploadTab").classList.remove("active");
    document.getElementById("cameraTab").classList.remove("active");
    const droidcamTab = document.getElementById("droidcamTab");
    if (droidcamTab) {
        droidcamTab.classList.remove("active");
    }
    
    // Remove active state from all buttons
    const tabButtons = document.querySelectorAll(".tab-btn");
    tabButtons.forEach(btn => btn.classList.remove("active"));
    
    // Show selected tab and mark button as active
    if (tab === "upload") {
        document.getElementById("uploadTab").classList.add("active");
        tabButtons[0].classList.add("active");
        // Stop camera if it was running
        if (cameraActive) {
            stopCamera();
        }
        // Disconnect DroidCam if connected
        if (droidcamConnected) {
            disconnectDroidcam();
        }
    } else if (tab === "camera") {
        document.getElementById("cameraTab").classList.add("active");
        tabButtons[1].classList.add("active");
        // Disconnect DroidCam if connected
        if (droidcamConnected) {
            disconnectDroidcam();
        }
    } else if (tab === "droidcam") {
        const droidcamTab = document.getElementById("droidcamTab");
        if (droidcamTab) {
            droidcamTab.classList.add("active");
        }
        tabButtons[2].classList.add("active");
        // Stop camera if it was running
        if (cameraActive) {
            stopCamera();
        }
    }
}

// Start Camera
function startCamera() {
    hideOCRError();

    // Updated constraints to prioritize front camera explicitly
    const constraints = [
        {
            video: {
                facingMode: { exact: "user" }, // Explicitly request front camera
                width: { ideal: 1280 },
                height: { ideal: 720 }
            },
            audio: false
        },
        {
            video: {
                facingMode: "user" // Fallback to general front camera request
            },
            audio: false
        },
        {
            video: true, // General video request as last resort
            audio: false
        }
    ];

    function attemptGetUserMedia(constraintIndex) {
        if (constraintIndex >= constraints.length) {
            showOCRError("Unable to access camera on this device.");
            return;
        }

        navigator.mediaDevices.getUserMedia(constraints[constraintIndex])
            .then(stream => {
                cameraStream = stream;
                cameraActive = true;

                const video = document.getElementById("cameraPreview");
                video.srcObject = stream;

                // Wait for video to be ready
                video.onloadedmetadata = () => {
                    video.play().then(() => {
                        video.classList.add("active");

                        // Update UI
                        document.getElementById("startCameraBtn").style.display = "none";
                        document.getElementById("captureBtn").style.display = "block";
                        document.getElementById("stopCameraBtn").style.display = "block";
                    }).catch(err => {
                        console.error("Video play error:", err);
                        // Stop tracks for this stream before trying next
                        stream.getTracks().forEach(t => t.stop());
                        attemptGetUserMedia(constraintIndex + 1);
                    });
                };
            })
            .catch(error => {
                console.error("Camera access error:", error);
                // Provide clearer UI error for permission/availability issues
                if (error && (error.name === 'NotAllowedError' || error.name === 'SecurityError')) {
                    showOCRError('Camera access was denied. Please allow camera permissions and try again.');
                    return;
                }
                if (error && error.name === 'NotFoundError') {
                    showOCRError('No camera found on this device.');
                    return;
                }
                // Try next constraint set
                attemptGetUserMedia(constraintIndex + 1);
            });
    }

    attemptGetUserMedia(0);
}

// Stop Camera
function stopCamera() {
    if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
        cameraActive = false;
    }
    
    const video = document.getElementById("cameraPreview");
    video.srcObject = null;
    video.classList.remove("active");
    
    // Update UI
    document.getElementById("startCameraBtn").style.display = "block";
    document.getElementById("captureBtn").style.display = "none";
    document.getElementById("stopCameraBtn").style.display = "none";

    // Revoke any captured image URL to free memory
    if (window._lastCapturedUrl) {
        URL.revokeObjectURL(window._lastCapturedUrl);
        window._lastCapturedUrl = null;
    }
}

// Capture Frame from Camera
function captureFrame() {
    const video = document.getElementById("cameraPreview");
    const canvas = document.getElementById("captureCanvas");
    const ctx = canvas.getContext("2d");
    
    // Check if video is loaded and has dimensions
    if (video.videoWidth === 0 || video.videoHeight === 0) {
        showOCRError("Camera not ready. Please wait a moment and try again.");
        return;
    }
    
    try {
        // Set canvas size to match video
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        
        // Draw video frame to canvas
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        
        // Convert canvas to blob and store it. Provide a dataURL fallback for older browsers.
        if (canvas.toBlob) {
            canvas.toBlob(blob => {
                if (!blob) {
                    showOCRError("Failed to capture image. Please try again.");
                    return;
                }
                capturedBlob = blob;
                displayCapturedImage();
            }, "image/jpeg", 0.95);
        } else {
            try {
                const dataUrl = canvas.toDataURL('image/jpeg', 0.95);
                // Convert dataURL to Blob
                const byteString = atob(dataUrl.split(',')[1]);
                const ab = new ArrayBuffer(byteString.length);
                const ia = new Uint8Array(ab);
                for (let i = 0; i < byteString.length; i++) ia[i] = byteString.charCodeAt(i);
                const blob = new Blob([ab], { type: 'image/jpeg' });
                capturedBlob = blob;
                displayCapturedImage();
            } catch (err) {
                console.error('Capture fallback error:', err);
                showOCRError('Failed to capture image (fallback).');
            }
        }
    } catch (error) {
        console.error("Capture error:", error);
        showOCRError("Failed to capture image: " + error.message);
    }
}

// Display Captured Image
function displayCapturedImage() {
    if (!capturedBlob) {
        showOCRError("No image captured. Please try again.");
        return;
    }
    
    // Revoke previous preview URL if present
    if (window._lastCapturedUrl) {
        URL.revokeObjectURL(window._lastCapturedUrl);
        window._lastCapturedUrl = null;
    }

    const url = URL.createObjectURL(capturedBlob);
    window._lastCapturedUrl = url;

    const capturedImage = document.getElementById("capturedImage");
    const capturedImg = document.getElementById("capturedImg");

    capturedImg.src = url;
    capturedImage.style.display = "block";

    // Stop camera after capture
    stopCamera();
}

// Process Captured Image with OCR
function processCapturedImage() {
    if (!capturedBlob) {
        showOCRError("No image available. Please capture an image first.");
        return;
    }
    
    // Create file from stored blob
    const file = new File([capturedBlob], "captured_receipt.jpg", { type: "image/jpeg" });
    
    hideOCRResults();
    hideOCRError();
    document.getElementById("ocrLoading").style.display = "block";
    
    const formData = new FormData();
    formData.append("file", file);
    
    fetch("/api/ocr", {
        method: "POST",
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        document.getElementById("ocrLoading").style.display = "none";
        
        if (data.error) {
            showOCRError(data.error);
        } else {
            displayOCRResults(data);
        }
    })
    .catch(error => {
        document.getElementById("ocrLoading").style.display = "none";
        showOCRError("Error: " + error.message);
    });
}

// DroidCam Functions
function connectDroidcam() {
    const ip = document.getElementById("droidcamIp").value.trim();
    const port = document.getElementById("droidcamPort").value.trim() || "4747";
    
    if (!ip) {
        showOCRError("Please enter the DroidCam IP address");
        return;
    }
    
    hideOCRError();
    showOCRError("🔄 Connecting to DroidCam at " + ip + ":" + port + "...");
    
    // Use dedicated connectivity test endpoint which returns JSON quickly
    const testUrl = `/api/droidcam-test?ip=${ip}&port=${port}`;

    // Show a short timeout message after 12s if backend doesn't respond
    const timeoutMs = 12000;
    let timedOut = false;
    const timeout = setTimeout(() => {
        timedOut = true;
        showOCRError("⏱️ Connection timeout (12s). DroidCam server didn't respond. Ensure DroidCam app/server is running, IP/port are correct, and both devices are on the same network.");
    }, timeoutMs);

    fetch(testUrl)
        .then(response => response.json())
        .then(json => {
            clearTimeout(timeout);
            if (timedOut) return;

            if (json.status && json.status === 'success') {
                // Connection successful according to the backend test
                droidcamIp = ip;
                droidcamPort = port;
                droidcamConnected = true;

                hideOCRError();

                // Hide setup, show preview and controls
                document.querySelector(".droidcam-setup").style.display = "none";
                document.getElementById("droidcamPreview").style.display = "block";
                document.getElementById("droidcamControls").style.display = "flex";

                // Start refreshing the image (once per second)
                refreshDroidcamImage();
                droidcamRefreshInterval = setInterval(refreshDroidcamImage, 1000);

                showOCRError("✓ Connected to DroidCam successfully!");
                setTimeout(() => hideOCRError(), 2000);
            } else {
                // Connection failed - build detailed error message
                let errorMsg = "❌ Failed to connect to DroidCam at " + ip + ":" + port + "\n\n";
                
                // Show what endpoints were tried and their errors
                if (json.attempts && typeof json.attempts === 'object') {
                    errorMsg += "Endpoints tried:\n";
                    for (const [endpoint, error] of Object.entries(json.attempts)) {
                        errorMsg += "  • " + endpoint + ": " + error + "\n";
                    }
                    errorMsg += "\n";
                }
                
                errorMsg += "TROUBLESHOOTING:\n" +
                    "1. ✓ DroidCam app running on phone?\n" +
                    "2. ✓ Server started in DroidCam app?\n" +
                    "3. ✓ IP address correct? (Shown in DroidCam)\n" +
                    "4. ✓ Port correct? (Default: 4747)\n" +
                    "5. ✓ Same WiFi network?\n" +
                    "6. ✓ Firewall/VPN blocking?\n\n" +
                    "NOTE: If running in a remote container or Codespaces:\n" +
                    "  • Container may not reach your local phone on this network\n" +
                    "  • Run Flask on your host machine instead\n" +
                    "  • Or enable host networking in your dev container config";
                
                showOCRError(errorMsg);
            }
        })
        .catch(error => {
            clearTimeout(timeout);
            if (timedOut) return;

            console.error("DroidCam connection error:", error);
            showOCRError("❌ Connection error: " + (error.message || error) + "\n\nIf running in a container, try running the app on your host machine.\nOr enable host networking in your dev container.");
        });
}

function refreshDroidcamImage() {
    if (!droidcamIp) return;
    
    const timestamp = new Date().getTime();
    const apiUrl = `/api/droidcam?ip=${droidcamIp}&port=${droidcamPort}&t=${timestamp}`;
    
    const preview = document.getElementById("droidcamPreview");
    preview.src = apiUrl;
}

function captureDroidcamFrame() {
    if (!droidcamIp) {
        showOCRError("Not connected to DroidCam. Please connect first.");
        return;
    }
    
    hideOCRError();
    showOCRError("Capturing image...");
    
    const timestamp = new Date().getTime();
    const apiUrl = `/api/droidcam?ip=${droidcamIp}&port=${droidcamPort}&t=${timestamp}`;
    
    // Fetch the image from our backend proxy
    fetch(apiUrl)
        .then(response => {
            if (!response.ok) {
                throw new Error(`Server returned status ${response.status}`);
            }
            return response.blob();
        })
        .then(blob => {
            if (!blob) {
                showOCRError("Failed to capture image. Please try again.");
                return;
            }
            droidcamCapturedBlob = blob;
            hideOCRError();
            displayDroidcamCapturedImage();
        })
        .catch(error => {
            console.error("Capture error:", error);
            showOCRError("Failed to capture image. Verify DroidCam is running, IP is correct, and both devices are on the same network.");
        });
}

function displayDroidcamCapturedImage() {
    if (!droidcamCapturedBlob) {
        showOCRError("No image captured. Please try again.");
        return;
    }
    
    const url = URL.createObjectURL(droidcamCapturedBlob);
    const capturedImage = document.getElementById("droidcamCapturedImage");
    const capturedImg = document.getElementById("droidcamCapturedImg");
    
    capturedImg.src = url;
    capturedImage.style.display = "block";
    
    // Stop refreshing while showing captured image
    if (droidcamRefreshInterval) {
        clearInterval(droidcamRefreshInterval);
    }
}

function processDroidcamImage() {
    if (!droidcamCapturedBlob) {
        showOCRError("No image available. Please capture an image first.");
        return;
    }
    
    const file = new File([droidcamCapturedBlob], "droidcam_receipt.jpg", { type: "image/jpeg" });
    
    hideOCRResults();
    hideOCRError();
    document.getElementById("ocrLoading").style.display = "block";
    
    const formData = new FormData();
    formData.append("file", file);
    
    fetch("/api/ocr", {
        method: "POST",
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        document.getElementById("ocrLoading").style.display = "none";
        
        if (data.error) {
            showOCRError(data.error);
        } else {
            displayOCRResults(data);
        }
    })
    .catch(error => {
        document.getElementById("ocrLoading").style.display = "none";
        showOCRError("Error: " + error.message);
    });
}

function disconnectDroidcam() {
    if (droidcamRefreshInterval) {
        clearInterval(droidcamRefreshInterval);
    }
    
    droidcamConnected = false;
    droidcamIp = null;
    droidcamPort = 4747;
    droidcamCapturedBlob = null;
    
    // Show setup, hide preview and controls
    document.querySelector(".droidcam-setup").style.display = "block";
    document.getElementById("droidcamPreview").style.display = "none";
    document.getElementById("droidcamControls").style.display = "none";
    document.getElementById("droidcamCapturedImage").style.display = "none";
    
    hideOCRError();
}