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
            
            
class Observable:
    def __init__(self):
        # Instead of a list, use a dictionary keyed by observer_id.
        self._observers = {}
    
    def add_observer(self, observer_id, observer):
        """
        Registers an observer with the specified identifier.
        
        Args:
            observer_id (str): A unique identifier for the observer.
            observer (callable): The observer callback.
        """
        if observer_id not in self._observers:
            self._observers[observer_id] = observer

    def remove_observer(self, observer_id):
        """
        Removes the observer with the specified identifier.
        
        Args:
            observer_id (str): The unique identifier for the observer.
        """
        if observer_id in self._observers:
            del self._observers[observer_id]

    def notify_observers(self, *args, **kwargs):
        """
        Notifies all registered observers with the given arguments.
        """
        for observer in self._observers.values():
            observer(*args, **kwargs)

    def notify_observer_by_id(self, observer_id, *args, **kwargs):
        """
        Notifies a single observer specified by its identifier.
        
        Args:
            observer_id (str): The unique identifier of the observer to notify.
        """
        if observer_id in self._observers:
            self._observers[observer_id](*args, **kwargs)