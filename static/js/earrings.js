export function positionEarrings(landmarks, leftMesh, rightMesh, canvas) {
    if (!leftMesh || !canvas) return;

    const width = canvas.clientWidth || canvas.width;
    const height = canvas.clientHeight || canvas.height;

    // Convert MediaPipe coordinates to centered Three.js coordinates.
    const point = i => ({
        x: (0.5 - landmarks[i].x) * width,
        y: (0.5 - landmarks[i].y) * height
    });

    const leftEar = point(234);
    const rightEar = point(454);
    const leftEye = point(33);
    const rightEye = point(263);

    const eyeDistance = Math.hypot(
        rightEye.x - leftEye.x,
        rightEye.y - leftEye.y
    );

    // Earlobe sits below the tragus (increased drop to position earrings lower)
    const drop = eyeDistance * 0.52;

    const earTilt = Math.atan2(
        leftEye.y - rightEye.y,
        leftEye.x - rightEye.x
    );

    // Position left earring at left ear
    leftMesh.position.set(
        leftEar.x + eyeDistance * 0.05,
        leftEar.y - drop,
        0
    );
    leftMesh.rotation.z = earTilt;
    leftMesh.visible = true;

    // Position right earring at right ear
    if (rightMesh) {
        rightMesh.position.set(
            rightEar.x - eyeDistance * 0.05,
            rightEar.y - drop,
            0
        );
        rightMesh.rotation.z = earTilt;
        rightMesh.visible = true;
    }
}