from .manager import ModelsManager
from .benchmark import update_rankings
from .static import load_static_models
from ..colors import YELLOW, RED, BLUE, RESET

models_manager = ModelsManager()

def get_best_model(color: str) -> str:
    return models_manager.get_best_model(color)

def get_top_models(color: str, count: int = 3) -> list:
    return models_manager.get_top_models(color, count)

def show_rankings():
    models_manager.print_summary()

def init_models_manager():
    if not models_manager.rankings or not any(models_manager.rankings.values()):
        import threading
        from .benchmark import update_rankings
        info("Запуск первичного обновления ранкингов...")
        threading.Thread(target=update_rankings, args=(models_manager,), daemon=True).start()

def shutdown_models():
    models_manager.stop()

def model_color(model: str, fast_models: dict) -> str:
    if not fast_models:
        return RESET
    for color, models in fast_models.items():
        if model in models:
            return {"yellow": YELLOW, "red": RED, "blue": BLUE}[color]
    return RESET
