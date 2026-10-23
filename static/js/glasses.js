
export function positionGlasses(landmarks, mesh, canvas) {
    const width = canvas.clientWidth || canvas.width;
    const height = canvas.clientHeight || canvas.height;

    const point = i => ({
        x: (0.5 - landmarks[i].x) * width,
        y: (0.5 - landmarks[i].y) * height
    });

    const left = point(33);
    const right = point(263);

    const centerX = (left.x + right.x) / 2;
    const centerY = (left.y + right.y) / 2;

    const eyeDistance = Math.hypot(
        right.x - left.x,
        right.y - left.y
    );

    // Small downward adjustment relative to face size.
    const verticalOffset = eyeDistance * 0.05;

    mesh.position.set(
        centerX,
        centerY - verticalOffset,
        0
    );

    mesh.rotation.z = Math.atan2(
        left.y - right.y,
        left.x - right.x
    );

    mesh.visible = true;
}
