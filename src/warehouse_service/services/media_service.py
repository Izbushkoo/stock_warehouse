"""Media asset management service."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import List, Optional, BinaryIO
from uuid import UUID

from sqlmodel import Session, select

from warehouse_service.models.unified import (
    MediaAsset, MediaDerivative, ItemImage, DocumentFile, MovementAttachment,
    Item, StockMovement
)



class MediaService:
    """Service for media asset management and file operations."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def upload_media_asset(
        self,
        file_content: bytes,
        original_filename: str,
        mime_type: str,
        uploaded_by_user_id: UUID,
        storage_backend: str = "database",
        storage_bucket: Optional[str] = None,
        storage_key: Optional[str] = None,
        is_immutable: bool = True,
        worm_retention_days: Optional[int] = None,
    ) -> MediaAsset:
        """Upload and store a media asset."""
        
        # Calculate SHA-256 hash
        content_sha256 = hashlib.sha256(file_content).hexdigest()
        
        # Check if asset already exists
        existing_asset = self._get_asset_by_hash(content_sha256)
        if existing_asset:
            return existing_asset
        
        # Calculate retention date if specified
        worm_retention_until = None
        if worm_retention_days:
            worm_retention_until = datetime.utcnow().replace(
                day=datetime.utcnow().day + worm_retention_days
            )
        
        # Create media asset
        asset = MediaAsset(
            original_filename=original_filename,
            content_sha256=content_sha256,
            mime_type=mime_type,
            byte_size=len(file_content),
            storage_backend=storage_backend,
            storage_bucket=storage_bucket,
            storage_key=storage_key,
            stored_bytes=file_content if storage_backend == "database" else None,
            is_immutable=is_immutable,
            worm_retention_until=worm_retention_until,
            uploaded_by_user_id=uploaded_by_user_id,
        )
        
        self.session.add(asset)
        self.session.flush()
        
        # Generate derivatives for images
        if mime_type.startswith("image/"):
            self._generate_image_derivatives(asset, file_content)
        
        self.session.commit()
        self.session.refresh(asset)
        return asset
    
    def attach_image_to_item(
        self,
        item_id: UUID,
        media_asset_id: UUID,
        user_id: UUID,
        is_primary: bool = False,
        display_order: int = 100,
        alt_text: Optional[str] = None,
    ) -> ItemImage:
        """Attach an image to an item."""
        
        # Get item to check permissions
        item = self.session.get(Item, item_id)
        if not item:
            raise ValueError(f"Item {item_id} not found")
        
        # Check permissions (simplified - would need warehouse context)
        # For now, just check if user can upload media
        
        # Check if image already attached
        stmt = select(ItemImage).where(
            ItemImage.item_id == item_id,
            ItemImage.media_asset_id == media_asset_id,
        )
        existing = self.session.exec(stmt).first()
        if existing:
            return existing
        
        # If setting as primary, unset other primary images
        if is_primary:
            stmt = select(ItemImage).where(
                ItemImage.item_id == item_id,
                ItemImage.is_primary == True,
            )
            for existing_primary in self.session.exec(stmt):
                existing_primary.is_primary = False
        
        # Create item image
        item_image = ItemImage(
            item_id=item_id,
            media_asset_id=media_asset_id,
            is_primary=is_primary,
            display_order=display_order,
            alt_text=alt_text,
        )
        
        self.session.add(item_image)
        self.session.commit()
        self.session.refresh(item_image)
        return item_image
    
    def attach_document_to_operation(
        self,
        document_type: str,
        document_identifier: UUID,
        media_asset_id: UUID,
        document_file_role: str,
        uploaded_by_user_id: UUID,
    ) -> DocumentFile:
        """Attach a document to a business operation."""
        
        document_file = DocumentFile(
            document_type=document_type,
            document_identifier=document_identifier,
            media_asset_id=media_asset_id,
            document_file_role=document_file_role,
            uploaded_by_user_id=uploaded_by_user_id,
        )
        
        self.session.add(document_file)
        self.session.commit()
        self.session.refresh(document_file)
        return document_file
    
    def attach_file_to_movement(
        self,
        stock_movement_id: UUID,
        media_asset_id: UUID,
        attachment_role: str,
        user_id: UUID,
    ) -> MovementAttachment:
        """Attach a file to a stock movement."""
        
        # Verify movement exists and user has permission
        movement = self.session.get(StockMovement, stock_movement_id)
        if not movement:
            raise ValueError(f"Stock movement {stock_movement_id} not found")
        
        # Check if attachment already exists
        stmt = select(MovementAttachment).where(
            MovementAttachment.stock_movement_id == stock_movement_id,
            MovementAttachment.media_asset_id == media_asset_id,
            MovementAttachment.attachment_role == attachment_role,
        )
        existing = self.session.exec(stmt).first()
        if existing:
            return existing
        
        attachment = MovementAttachment(
            stock_movement_id=stock_movement_id,
            media_asset_id=media_asset_id,
            attachment_role=attachment_role,
        )
        
        self.session.add(attachment)
        self.session.commit()
        self.session.refresh(attachment)
        return attachment
    
    def get_media_asset(self, media_asset_id: UUID) -> Optional[MediaAsset]:
        """Get media asset by ID."""
        return self.session.get(MediaAsset, media_asset_id)
    
    def get_media_content(self, media_asset_id: UUID) -> Optional[bytes]:
        """Get media asset content."""
        asset = self.session.get(MediaAsset, media_asset_id)
        if not asset:
            return None
        
        if asset.storage_backend == "database":
            return asset.stored_bytes
        elif asset.storage_backend == "s3":
            # Would implement S3 retrieval here
            raise NotImplementedError("S3 storage not yet implemented")
        
        return None
    
    def get_media_derivative(
        self, 
        media_asset_id: UUID, 
        derivative_type: str
    ) -> Optional[MediaDerivative]:
        """Get media derivative by asset ID and type."""
        stmt = select(MediaDerivative).where(
            MediaDerivative.media_asset_id == media_asset_id,
            MediaDerivative.derivative_type == derivative_type,
        )
        return self.session.exec(stmt).first()
    
    def get_item_images(self, item_id: UUID) -> List[ItemImage]:
        """Get all images for an item."""
        stmt = select(ItemImage).where(
            ItemImage.item_id == item_id
        ).order_by(ItemImage.is_primary.desc(), ItemImage.display_order.asc())
        
        return list(self.session.exec(stmt))
    
    def get_primary_item_image(self, item_id: UUID) -> Optional[ItemImage]:
        """Get primary image for an item."""
        stmt = select(ItemImage).where(
            ItemImage.item_id == item_id,
            ItemImage.is_primary == True,
        )
        return self.session.exec(stmt).first()
    
    def get_movement_attachments(self, stock_movement_id: UUID) -> List[MovementAttachment]:
        """Get all attachments for a stock movement."""
        stmt = select(MovementAttachment).where(
            MovementAttachment.stock_movement_id == stock_movement_id
        )
        return list(self.session.exec(stmt))
    
    def get_document_files(
        self, 
        document_type: str, 
        document_identifier: UUID
    ) -> List[DocumentFile]:
        """Get all document files for a business operation."""
        stmt = select(DocumentFile).where(
            DocumentFile.document_type == document_type,
            DocumentFile.document_identifier == document_identifier,
        )
        return list(self.session.exec(stmt))
    
    def delete_media_asset(
        self, 
        media_asset_id: UUID, 
        user_id: UUID,
        force: bool = False
    ) -> bool:
        """Delete media asset if allowed."""
        asset = self.session.get(MediaAsset, media_asset_id)
        if not asset:
            return False
        
        # Check if asset is immutable
        if asset.is_immutable and not force:
            raise ValueError("Cannot delete immutable media asset")
        
        # Check WORM retention
        if asset.worm_retention_until and datetime.utcnow() < asset.worm_retention_until:
            raise ValueError("Cannot delete asset under WORM retention")
        
        # Check if asset is referenced
        if self._is_asset_referenced(media_asset_id):
            raise ValueError("Cannot delete asset that is referenced by other entities")
        
        # Delete derivatives first
        stmt = select(MediaDerivative).where(
            MediaDerivative.media_asset_id == media_asset_id
        )
        for derivative in self.session.exec(stmt):
            self.session.delete(derivative)
        
        # Delete the asset
        self.session.delete(asset)
        self.session.commit()
        return True
    
    def _get_asset_by_hash(self, content_sha256: str) -> Optional[MediaAsset]:
        """Get existing asset by content hash."""
        stmt = select(MediaAsset).where(MediaAsset.content_sha256 == content_sha256)
        return self.session.exec(stmt).first()
    
    def _generate_image_derivatives(self, asset: MediaAsset, content: bytes):
        """Generate image derivatives (thumbnails, previews)."""
        # This is a placeholder - would use PIL/Pillow for actual image processing
        
        derivatives_to_create = [
            {"type": "thumbnail_200", "width": 200, "height": 200},
            {"type": "preview_800", "width": 800, "height": 600},
            {"type": "webp_1200", "width": 1200, "height": 900},
        ]
        
        for derivative_spec in derivatives_to_create:
            # In real implementation, would resize image and convert format
            # For now, just create placeholder derivatives
            derivative = MediaDerivative(
                media_asset_id=asset.media_asset_id,
                derivative_type=derivative_spec["type"],
                mime_type="image/webp" if "webp" in derivative_spec["type"] else asset.mime_type,
                byte_size=len(content) // 2,  # Placeholder - would be actual resized size
                storage_backend=asset.storage_backend,
                storage_bucket=asset.storage_bucket,
                storage_key=f"{asset.storage_key}_{derivative_spec['type']}" if asset.storage_key else None,
                stored_bytes=content[:len(content)//2] if asset.storage_backend == "database" else None,
                pixel_width=derivative_spec["width"],
                pixel_height=derivative_spec["height"],
            )
            
            self.session.add(derivative)
    
    def _is_asset_referenced(self, media_asset_id: UUID) -> bool:
        """Check if media asset is referenced by other entities."""
        
        # Check item images
        stmt = select(ItemImage).where(ItemImage.media_asset_id == media_asset_id)
        if self.session.exec(stmt).first():
            return True
        
        # Check document files
        stmt = select(DocumentFile).where(DocumentFile.media_asset_id == media_asset_id)
        if self.session.exec(stmt).first():
            return True
        
        # Check movement attachments
        stmt = select(MovementAttachment).where(MovementAttachment.media_asset_id == media_asset_id)
        if self.session.exec(stmt).first():
            return True
        
        return False
    
    def create_media_from_upload(
        self,
        file: BinaryIO,
        filename: str,
        content_type: str,
        user_id: UUID,
        storage_backend: str = "database",
    ) -> MediaAsset:
        """Create media asset from file upload."""
        
        # Read file content
        content = file.read()
        file.seek(0)  # Reset file pointer
        
        return self.upload_media_asset(
            file_content=content,
            original_filename=filename,
            mime_type=content_type,
            uploaded_by_user_id=user_id,
            storage_backend=storage_backend,
        )
    
    def get_asset_url(self, media_asset_id: UUID, derivative_type: Optional[str] = None) -> Optional[str]:
        """Get URL for accessing media asset or derivative."""
        
        if derivative_type:
            derivative = self.get_media_derivative(media_asset_id, derivative_type)
            if not derivative:
                return None
            
            if derivative.storage_backend == "s3":
                # Would generate S3 URL
                return f"s3://{derivative.storage_bucket}/{derivative.storage_key}"
            else:
                # Database storage - return API endpoint
                return f"/api/media/{media_asset_id}/derivative/{derivative_type}"
        else:
            asset = self.get_media_asset(media_asset_id)
            if not asset:
                return None
            
            if asset.storage_backend == "s3":
                return f"s3://{asset.storage_bucket}/{asset.storage_key}"
            else:
                return f"/api/media/{media_asset_id}"
    
    def validate_file_upload(
        self,
        filename: str,
        content_type: str,
        file_size: int,
        max_size_mb: int = 50,
        allowed_types: Optional[List[str]] = None,
    ) -> bool:
        """Validate file upload parameters."""
        
        # Check file size
        if file_size > max_size_mb * 1024 * 1024:
            raise ValueError(f"File size {file_size} exceeds maximum {max_size_mb}MB")
        
        # Check content type
        if allowed_types and content_type not in allowed_types:
            raise ValueError(f"Content type {content_type} not allowed")
        
        # Check filename
        if not filename or len(filename) > 255:
            raise ValueError("Invalid filename")
        
        return True