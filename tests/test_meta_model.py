import pytest

backend_modules = pytest.importorskip("backend.schemas", reason="backend dependencies missing")
meta_modules = pytest.importorskip("engine.meta_model", reason="engine dependencies missing")

LivePacket = backend_modules.LivePacket
ShapItem = backend_modules.ShapItem
MetaModel = meta_modules.MetaModel
MetaModelConfig = meta_modules.MetaModelConfig


def test_meta_model_smoothing():
    model = MetaModel(MetaModelConfig(alpha=0.5))
    packet = LivePacket(
        gid="demo",
        ts=1,
        y_pred=0.5,
        state={},
        shap=[ShapItem(f="QB_pressure_rate", s=0.1)],
        model_version="v0",
    )
    result = model.update(packet)
    assert 0.0 <= result.p_win <= 1.0
