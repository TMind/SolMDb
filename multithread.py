def run(self, data):
    num_items = len(data)
    num_threads = min(num_items, threading.active_count())
    threads = []
    results = []

    def worker(data_chunk):
        result = self.function(data_chunk)
        results.append(result)

    chunk_size = num_items // num_threads
    for i in range(num_threads):
        start = i * chunk_size
        end = start + chunk_size if i < num_threads - 1 else num_items
        thread = threading.Thread(target=worker, args=(data[start:end],))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    return results
