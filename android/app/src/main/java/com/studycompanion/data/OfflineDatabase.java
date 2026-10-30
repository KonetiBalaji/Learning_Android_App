package com.studycompanion.data;

import androidx.room.Database;
import androidx.room.RoomDatabase;

@Database(entities = {OfflineRecord.class}, version = 1, exportSchema = false)
public abstract class OfflineDatabase extends RoomDatabase {
    public abstract OfflineDao records();
}
