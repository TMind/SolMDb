class DataSelectionManager:
    observers = []

    @staticmethod
    def update_data(event, widget):
        DataSelectionManager.notify_observers(event, widget)

    @staticmethod
    def register_observer(observer_func):
        DataSelectionManager.observers.append(observer_func)

    @staticmethod
    def unregister_observer(observer_func):
        DataSelectionManager.observers.remove(observer_func)

    @staticmethod
    def notify_observers(event, widget):
        for observer in DataSelectionManager.observers:
            observer(event, widget)