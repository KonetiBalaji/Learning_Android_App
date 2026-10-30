package com.studycompanion.data;

import androidx.room.Dao;
import androidx.room.Insert;
import androidx.room.OnConflictStrategy;
import androidx.room.Query;
import java.util.List;

@Dao
public interface OfflineDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE) void save(OfflineRecord record);
    @Query("SELECT * FROM offline_records WHERE scope=:scope AND id=:id") OfflineRecord get(String scope, String id);
    @Query("SELECT * FROM offline_records WHERE scope=:scope ORDER BY id") List<OfflineRecord> all(String scope);
    @Query("DELETE FROM offline_records WHERE scope=:scope AND id=:id") void delete(String scope, String id);
    @Query("DELETE FROM offline_records WHERE expiresAt<=:now") void purge(long now);
    @Query("DELETE FROM offline_records") void clear();
}
