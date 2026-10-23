
export function positionEarrings(landmarks, leftMesh, rightMesh, canvas) {
    if (!leftMesh || !canvas) return;

    const width = canvas.clientWidth || canvas.width;
    const height = canvas.clientHeight || canvas.height;

    // Convert MediaPipe landmarks to mirrored canvas coordinates.
    const point = i => ({
        x: (0.5 - landmarks[i].x) * width,
        y: (0.5 - landmarks[i].y) * height
    });

    const leftEar = point(234);
    const rightEar = point(454);
    const leftEye = point(33);
    const rightEye = point(263);

    // Estimate face scale from the distance between the eyes.
    const eyeDistance = Math.hypot(
        rightEye.x - leftEye.x,
        rightEye.y - leftEye.y
    );

    if (eyeDistance <= 0) return;

    // Approximate average adult interpupillary distance (in mm).
    // This is an estimate, not an individual measurement.
    const REFERENCE_EYE_DISTANCE_MM = 63;

    // Read actual product dimensions from the backend data.
    const product = window.AR_PRODUCT || {};
    const widthMM = Number(product.width_mm);
    const heightMM = Number(product.height_mm);

    if (
        !Number.isFinite(widthMM) || widthMM <= 0 ||
        !Number.isFinite(heightMM) || heightMM <= 0
    ) {
        leftMesh.visible = false;
        if (rightMesh) rightMesh.visible = false;
        return;
    }

    // Convert physical dimensions to approximate screen pixels.
    const pixelsPerMM = eyeDistance / REFERENCE_EYE_DISTANCE_MM;
    const targetWidth = widthMM * pixelsPerMM;
    const targetHeight = heightMM * pixelsPerMM;

    // Scale the mesh while preserving the supplied physical dimensions.
    const baseWidth = leftMesh.geometry.parameters.width;
    const baseHeight = leftMesh.geometry.parameters.height;

    if (!baseWidth || !baseHeight) return;

    const scaleX = targetWidth / baseWidth;
    const scaleY = targetHeight / baseHeight;

    leftMesh.scale.set(scaleX, scaleY, 1);

    if (rightMesh) {
        rightMesh.scale.set(scaleX, scaleY, 1);
    }

    // Position the earrings relative to the detected ears.
    const drop = eyeDistance * 0.45;
    const horizontalOffset = eyeDistance * 0.03;

    const earTilt = Math.atan2(
        leftEye.y - rightEye.y,
        leftEye.x - rightEye.x
    );

    function positionEarring(mesh, ear, direction) {
        if (!mesh) return;

        const renderedHeight =
            mesh.geometry.parameters.height * mesh.scale.y;

        const anchorX = ear.x + direction * horizontalOffset;
        const anchorY = ear.y - drop;

        mesh.position.set(
            anchorX,
            anchorY - renderedHeight / 2,
            0
        );

        mesh.rotation.z = earTilt;
        mesh.visible = true;
    }

    positionEarring(leftMesh, leftEar, 1);
    positionEarring(rightMesh, rightEar, -1);
}
