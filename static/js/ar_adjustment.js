(() => {
    const ids = {
        x: 'arMoveX',
        y: 'arMoveY',
        scale: 'arScale',
        rotation: 'arRotation'
    };

    const controls = Object.fromEntries(
        Object.entries(ids).map(([key, id]) => [
            key, document.getElementById(id)
        ])
    );

    window.AR_ADJUSTMENTS = {
        x: 0,
        y: 0,
        scale: 1,
        rotation: 0
    };

    function update() {
        window.AR_ADJUSTMENTS = {
            x: Number(controls.x.value),
            y: Number(controls.y.value),
            scale: Number(controls.scale.value) / 100,
            rotation: Number(controls.rotation.value) * Math.PI / 180
        };

        document.getElementById('arMoveXValue').textContent =
            `${controls.x.value}px`;
        document.getElementById('arMoveYValue').textContent =
            `${controls.y.value}px`;
        document.getElementById('arScaleValue').textContent =
            `${controls.scale.value}%`;
        document.getElementById('arRotationValue').textContent =
            `${controls.rotation.value}°`;
    }

    Object.values(controls).forEach(control => {
        control.addEventListener('input', update);
    });

    document.getElementById('resetARAdjustments')
        .addEventListener('click', () => {
            controls.x.value = 0;
            controls.y.value = 0;
            controls.scale.value = 100;
            controls.rotation.value = 0;
            update();
        });

    update();
})();
