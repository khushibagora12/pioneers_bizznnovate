import * as THREE from 'https://cdn.jsdelivr.net/npm/three@0.180.0/build/three.module.js'
import { positionEarrings } from './earrings.js';
import { positionGlasses } from './glasses.js';

const video = document.getElementById('camera');
const canvas = document.getElementById('canvas');

const status = document.getElementById('status');
const placeholder = document.getElementById('placeholder');
const startButton = document.getElementById('startButton');
const stopButton = document.getElementById('stopButton');
const captureButton = document.getElementById('captureButton');

let cameraStream = null;
let faceLandmarker = null;
let animationId = null;
let isRunning = false;
let lastVideoTime = -1;

let selectedImage = null;
let jewelleryTexture = null;
let selectedCategory = null;
let jewelleryMesh = null;
let rightEarringMesh = null;
const userAdjustments = {
    x: 0,
    y: 0,
    scale: 1,
    rotation: 0
};


const adjustX = document.getElementById('adjustX');
const adjustY = document.getElementById('adjustY');
const adjustSize = document.getElementById('adjustSize');
const adjustRotation = document.getElementById('adjustRotation');
const resetAdjustments = document.getElementById('resetAdjustments');


function updateAdjustmentLabels() {
    const xLabel = document.getElementById('adjustXValue');
    const yLabel = document.getElementById('adjustYValue');
    const sizeLabel = document.getElementById('adjustSizeValue');
    const rotationLabel = document.getElementById('adjustRotationValue');

    if (xLabel) xLabel.textContent = `${Math.round(userAdjustments.x)}px`;
    if (yLabel) yLabel.textContent = `${Math.round(userAdjustments.y)}px`;
    if (sizeLabel) {
        sizeLabel.textContent =
            `${Math.round(userAdjustments.scale * 100)}%`;
    }
    if (rotationLabel) {
        rotationLabel.textContent =
            `${Math.round(userAdjustments.rotation * 180 / Math.PI)}°`;
    }
}

adjustX?.addEventListener('input', () => {
    userAdjustments.x = Number(adjustX.value);
    updateAdjustmentLabels();
});

adjustY?.addEventListener('input', () => {
    userAdjustments.y = Number(adjustY.value);
    updateAdjustmentLabels();
});

adjustSize?.addEventListener('input', () => {
    userAdjustments.scale = Number(adjustSize.value) / 100;
    updateAdjustmentLabels();
});

adjustRotation?.addEventListener('input', () => {
    userAdjustments.rotation =
        Number(adjustRotation.value) * Math.PI / 180;
    updateAdjustmentLabels();
});

resetAdjustments?.addEventListener('click', () => {
    userAdjustments.x = 0;
    userAdjustments.y = 0;
    userAdjustments.scale = 1;
    userAdjustments.rotation = 0;

    if (adjustX) adjustX.value = 0;
    if (adjustY) adjustY.value = 0;
    if (adjustSize) adjustSize.value = 100;
    if (adjustRotation) adjustRotation.value = 0;

    updateAdjustmentLabels();
});

updateAdjustmentLabels();


let isDragging = false;
let lastPointerX = 0;
let lastPointerY = 0;

const scene = new THREE.Scene();

const arCamera = new THREE.OrthographicCamera(
    -canvas.clientWidth / 2,
    canvas.clientWidth / 2,
    canvas.clientHeight / 2,
    -canvas.clientHeight / 2,
    0.1,
    1000
);
arCamera.position.z = 100;
const renderer = new THREE.WebGLRenderer({
    canvas,
    alpha: true,
    antialias: true,
    preserveDrawingBuffer: true
});
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
renderer.setClearColor(0x000000, 0);
renderer.outputColorSpace = THREE.SRGBColorSpace;


const WASM_URL =
    'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/wasm';

const MODEL_URL =
    'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task';


const categoryNames = {
    earrings: 'Earrings',
    shades: 'Shades',
};

function setStatus(message) {
    if (status) status.textContent = message;
}
// Receive the product selected on the dashboard.
function setARProduct(product) {
    if (!product) return;

    const category = String(product.category || '').toLowerCase();

    if (!categoryNames[category]) {
        userAdjustments.x = 0;
        userAdjustments.y = 0;
        userAdjustments.scale = 1;
        userAdjustments.rotation = 0;

        selectedImage = null;
        selectedCategory = null;
        removeJewellery();

        console.error('Unsupported AR category:', category);
        setStatus(`AR is not configured for ${category}.`);
        return;
    }
    const image = product.image;

    if (!image || !image.complete || !image.naturalWidth) {
        console.error('AR product image is not loaded.');
        setStatus('The jewellery image has not loaded.');
        return;
    }
    selectedImage = image;
    selectedCategory = category;

    loadJewelleryTexture(image);

    setStatus(
        isRunning
            ? 'Product selected. Position your face in the camera.'
            : 'Product ready. Start the camera.'
    );

    console.log('AR product selected:', category, product.productId);
}

function removeJewellery() {
    if (jewelleryMesh) {
        scene.remove(jewelleryMesh);
        jewelleryMesh.geometry.dispose();
        jewelleryMesh.material.dispose();
        jewelleryMesh = null;
    }

    if (rightEarringMesh) {
        scene.remove(rightEarringMesh);
        rightEarringMesh = null;
    }

    if (jewelleryTexture) {
        jewelleryTexture.dispose();
        jewelleryTexture = null;
    }
}
function loadJewelleryTexture(image) {
    removeJewellery();

    jewelleryTexture = new THREE.Texture(image);
    jewelleryTexture.colorSpace = THREE.SRGBColorSpace;
    jewelleryTexture.needsUpdate = true;

    const material = new THREE.MeshBasicMaterial({
        map: jewelleryTexture,
        transparent: true,
        opacity: 1,
        side: THREE.DoubleSide,
        depthTest: false,
        depthWrite: false
    });

    // A textured plane is the initial AR representation of the product.
    const aspect = image.naturalWidth / image.naturalHeight;
    const initialHeight = Math.min(canvas.clientHeight * 0.35, 300);

    const geometry = new THREE.PlaneGeometry(
        initialHeight * aspect,
        initialHeight
    );

    jewelleryMesh = new THREE.Mesh(geometry, material);
    jewelleryMesh.position.set(0, 0, 0);
    jewelleryMesh.renderOrder = 10;
    jewelleryMesh.visible = false;
    scene.add(jewelleryMesh);

    if (selectedCategory === 'earrings') {
        rightEarringMesh = new THREE.Mesh(geometry, material);
        rightEarringMesh.position.set(0, 0, 0);
        rightEarringMesh.renderOrder = 10;
        rightEarringMesh.visible = false;
        scene.add(rightEarringMesh);
    }
}

window.addEventListener('ar-product-ready', event => {
    setARProduct(event.detail);
});

// Handle the case where the product event fired before this module loaded.
if (window.AR_PRODUCT) {
    setARProduct(window.AR_PRODUCT);
}

async function initializeFaceLandmarker() {
    if (faceLandmarker) return;

    setStatus('Loading face tracking model...');

    const { FilesetResolver, FaceLandmarker } = await import(
        'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/vision_bundle.mjs'
    );

    const vision = await FilesetResolver.forVisionTasks(WASM_URL);

    faceLandmarker = await FaceLandmarker.createFromOptions(vision, {
        baseOptions: {
            modelAssetPath: MODEL_URL
        },
        runningMode: 'VIDEO',
        numFaces: 1,
        outputFacialTransformationMatrixes: true
    });
}

async function startCamera() {
    if (cameraStream || isRunning) return;

    if (!navigator.mediaDevices?.getUserMedia) {
        setStatus('Camera unavailable. Use localhost or HTTPS.');
        return;
    }

    startButton.disabled = true;
    setStatus('Requesting camera permission...');

    try {
        cameraStream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: 'user' },
            audio: false
        });

        video.srcObject = cameraStream;
        await video.play();

        video.style.display = 'block';

        if (placeholder) placeholder.style.display = 'none';

        resizeCanvas();
        await initializeFaceLandmarker();

        isRunning = true;
        lastVideoTime = -1;

        startButton.textContent = 'Camera started';
        stopButton.disabled = false;

        if (captureButton) captureButton.disabled = false;

        setStatus('Looking for your face...');
        renderLoop();
    } catch (error) {
        console.error('Camera or face tracking error:', error);
        stopCamera();
        setStatus(
            'Could not start the camera or face tracking. Check permissions and connection.'
        );
        startButton.disabled = false;
        startButton.textContent = 'Start camera';
    }
}

function resizeCanvas() {
    const container = document.querySelector('.camera-stage');
    if (!container) return;

    const width = Math.max(1, container.clientWidth);
    const height = Math.max(1, container.clientHeight);

    renderer.setSize(width, height, false);

    arCamera.left = -width / 2;
    arCamera.right = width / 2;
    arCamera.top = height / 2;
    arCamera.bottom = -height / 2;
    arCamera.updateProjectionMatrix();

    // Rebuild the product plane at the new display scale.
    if (selectedImage && selectedImage.complete) {
        loadJewelleryTexture(selectedImage);
    }
}

function landmarkToScreen(landmark) {
    const width = canvas.clientWidth || canvas.width;
    const height = canvas.clientHeight || canvas.height;
    return {
        x: (0.5 - landmark.x) * width,
        y: (0.5 - landmark.y) * height
    };
}

function distance(a, b) {
    return Math.hypot(b.x - a.x, b.y - a.y);
}

function positionJewellery(landmarks) {
    if (!jewelleryMesh || !selectedImage || !selectedCategory) return;

    const width = canvas.clientWidth || canvas.width;
    const height = canvas.clientHeight || canvas.height;

    const leftEye = {
        x: (0.5 - landmarks[33].x) * width,
        y: (0.5 - landmarks[33].y) * height
    };

    const rightEye = {
        x: (0.5 - landmarks[263].x) * width,
        y: (0.5 - landmarks[263].y) * height
    };

    const eyeDistance = Math.hypot(
        rightEye.x - leftEye.x,
        rightEye.y - leftEye.y
    );

    const widthFactors = {
        earrings: 0.50,
        shades: 1.5,
    };

    const factor = widthFactors[selectedCategory];
    if (!factor) {
        jewelleryMesh.visible = false;
        if (rightEarringMesh) rightEarringMesh.visible = false;
        return;
    }

    const meshWidth = eyeDistance * factor;
    const aspect = selectedImage.naturalWidth / selectedImage.naturalHeight;
    const meshHeight = meshWidth / aspect;

    // Scale the mesh relative to its original plane dimensions.
    jewelleryMesh.scale.set(
        meshWidth / jewelleryMesh.geometry.parameters.width,
        meshHeight / jewelleryMesh.geometry.parameters.height,
        1
    );

    if (rightEarringMesh) {
        rightEarringMesh.scale.copy(jewelleryMesh.scale);
        rightEarringMesh.rotation.z = 0;
    }

    jewelleryMesh.rotation.z = 0;

    switch (selectedCategory) {
        case 'earrings':
            positionEarrings(landmarks, jewelleryMesh, rightEarringMesh, canvas);
            break;

        case 'shades':
            if (rightEarringMesh) rightEarringMesh.visible = false;
            positionGlasses(landmarks, jewelleryMesh, canvas);
            break;

        default:
            jewelleryMesh.visible = false;
            if (rightEarringMesh) rightEarringMesh.visible = false;
    }
    function applyUserAdjustment(mesh) {
        if (!mesh || !mesh.visible) return;

        mesh.position.x += userAdjustments.x;
        mesh.position.y -= userAdjustments.y;

        mesh.scale.x *= userAdjustments.scale;
        mesh.scale.y *= userAdjustments.scale;

        mesh.rotation.z += userAdjustments.rotation;
    }

    applyUserAdjustment(jewelleryMesh);

    if (selectedCategory === 'earrings') {
        applyUserAdjustment(rightEarringMesh);
    }
}


const gestureArea = document.querySelector('.camera-stage');

if (gestureArea) {
    gestureArea.style.touchAction = 'none';

    gestureArea.addEventListener('pointerdown', event => {
        if (!isRunning || !jewelleryMesh?.visible) return;

        // Only allow the left mouse button on a computer.
        if (event.pointerType === 'mouse' && event.button !== 0) return;

        event.preventDefault();
        gestureArea.setPointerCapture(event.pointerId);

        isDragging = true;
        lastPointerX = event.clientX;
        lastPointerY = event.clientY;
    });

    gestureArea.addEventListener('pointermove', event => {
        if (!isDragging) return;

        event.preventDefault();

        const dx = event.clientX - lastPointerX;
        const dy = event.clientY - lastPointerY;

        userAdjustments.x += dx;
        userAdjustments.y += dy;

        lastPointerX = event.clientX;
        lastPointerY = event.clientY;
    });

    function stopDragging() {
        isDragging = false;
    }

    gestureArea.addEventListener('pointerup', stopDragging);
    gestureArea.addEventListener('pointercancel', stopDragging);
    gestureArea.addEventListener('lostpointercapture', stopDragging);
}

function renderLoop() {
    if (!isRunning) return;

    animationId = requestAnimationFrame(renderLoop);

    if (
        !faceLandmarker ||
        video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA ||
        video.currentTime === lastVideoTime
    ) {
        renderer.render(scene, arCamera);
        return;
    }

    lastVideoTime = video.currentTime;

    const results = faceLandmarker.detectForVideo(
        video,
        performance.now()
    );

    const faces = results.faceLandmarks;

    if (!faces || faces.length === 0) {
        if (jewelleryMesh) jewelleryMesh.visible = false;
        if (rightEarringMesh) rightEarringMesh.visible = false;
        setStatus('No face detected.');
        renderer.render(scene, arCamera);
        return;
    }

    if (selectedImage && selectedCategory) {
        positionJewellery(faces[0]);
        setStatus('Face detected. Adjust your position as needed.');
    } else {
        if (jewelleryMesh) jewelleryMesh.visible = false;
        if (rightEarringMesh) rightEarringMesh.visible = false;
        setStatus('Face detected. No AR product selected.');
    }

    renderer.render(scene, arCamera);
}

function stopCamera() {
    isRunning = false;

    if (animationId !== null) {
        cancelAnimationFrame(animationId);
        animationId = null;
    }

    if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
        cameraStream = null;
    }

    if (video) {
        video.srcObject = null;
        video.style.display = 'none';
    }

    if (placeholder) placeholder.style.display = 'flex';

    if (jewelleryMesh) jewelleryMesh.visible = false;
    if (rightEarringMesh) rightEarringMesh.visible = false;
    renderer.clear();

    setStatus('Camera is currently off.');

    startButton.disabled = false;
    startButton.textContent = 'Start camera';
    stopButton.disabled = true;

    if (captureButton) captureButton.disabled = true;

    lastVideoTime = -1;
}

function captureLook() {
    if (!isRunning || !video.videoWidth) return;

    // Ensure the latest Three.js frame is available for capture.
    renderer.render(scene, arCamera);

    const output = document.createElement('canvas');
    output.width = canvas.width;
    output.height = canvas.height;

    const outputCtx = output.getContext('2d');

    const videoAspect = video.videoWidth / video.videoHeight;
    const canvasAspect = output.width / output.height;

    let drawWidth;
    let drawHeight;
    let offsetX = 0;
    let offsetY = 0;

    if (videoAspect > canvasAspect) {
        drawHeight = output.height;
        drawWidth = drawHeight * videoAspect;
        offsetX = (output.width - drawWidth) / 2;
    } else {
        drawWidth = output.width;
        drawHeight = drawWidth / videoAspect;
        offsetY = (output.height - drawHeight) / 2;
    }

    // Mirror the video to match the preview and landmark positions.
    outputCtx.save();
    outputCtx.translate(output.width, 0);
    outputCtx.scale(-1, 1);
    outputCtx.drawImage(video, offsetX, offsetY, drawWidth, drawHeight);
    outputCtx.restore();

    outputCtx.drawImage(canvas, 0, 0);

    const link = document.createElement('a');
    link.download = 'lumiar-try-on.png';
    link.href = output.toDataURL('image/png');
    link.click();
}

startButton.addEventListener('click', startCamera);
stopButton.addEventListener('click', stopCamera);
captureButton?.addEventListener('click', captureLook);

window.addEventListener('pagehide', stopCamera);
window.addEventListener('resize', resizeCanvas);