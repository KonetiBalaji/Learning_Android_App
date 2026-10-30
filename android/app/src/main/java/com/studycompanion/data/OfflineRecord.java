package com.studycompanion.data;

import androidx.annotation.NonNull;
import androidx.room.Entity;
import androidx.room.PrimaryKey;

/** Only opaque identifiers and expiry are indexed; all content is authenticated ciphertext. */
@Entity(tableName = "offline_records")
public class OfflineRecord {
    @PrimaryKey @NonNull public String id = "";
    @NonNull public String scope = "";
    public long expiresAt;
    @NonNull public byte[] payload = new byte[0];
}
