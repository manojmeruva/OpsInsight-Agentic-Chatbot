from abc import ABC, abstractmethod
from typing import List, Dict

class RepositoryBase(ABC):
    @abstractmethod
    def create(self, data: dict):
        """Create a new record in the database"""
        pass
    
    @abstractmethod
    def aggregate(self,pipeline):
        """Aggregate data from the database"""
        pass

    @abstractmethod
    def get_all(self, limit: int) -> List[Dict]:
        """Retrieve all records, limited by the provided number"""
        pass

    @abstractmethod
    def get_by_id(self, id: str) -> Dict:
        """Get a record by ID"""
        pass

    @abstractmethod
    def update(self, id: str, data: dict):
        """Update a record"""
        pass

    @abstractmethod
    def delete(self, id: str):
        """Delete a record"""
        pass
