"""Analytics and reporting service."""

from __future__ import annotations

from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlmodel import Session, select, func, and_, or_

from warehouse_service.models.unified import (
    SalesAnalytics, PurchaseRecommendation, StockBalance, StockMovement,
    Item, ItemGroup, Warehouse, SalesOrder, SalesOrderLine
)



class AnalyticsService:
    """Service for analytics, reporting, and purchase recommendations."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_sales_analytics(
        self,
        warehouse_id: UUID,
        user_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        marketplace_channel: Optional[str] = None,
        item_id: Optional[UUID] = None,
        group_by: str = "day",  # day, week, month, item, marketplace
    ) -> List[Dict[str, Any]]:
        """Get sales analytics with various grouping options."""
        
        # Build base query
        stmt = select(SalesAnalytics).where(SalesAnalytics.warehouse_id == warehouse_id)
        
        if start_date:
            stmt = stmt.where(SalesAnalytics.sale_date >= start_date)
        if end_date:
            stmt = stmt.where(SalesAnalytics.sale_date <= end_date)
        if marketplace_channel:
            stmt = stmt.where(SalesAnalytics.marketplace_channel == marketplace_channel)
        if item_id:
            stmt = stmt.where(SalesAnalytics.item_id == item_id)
        
        analytics = list(self.session.exec(stmt))
        
        # Group and aggregate results
        return self._group_analytics_results(analytics, group_by)
    
    def get_inventory_turnover(
        self,
        warehouse_id: UUID,
        user_id: UUID,
        period_days: int = 90,
        item_group_id: Optional[UUID] = None,
    ) -> List[Dict[str, Any]]:
        """Calculate inventory turnover rates."""
        

        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=period_days)
        
        # Get sales data for the period
        stmt = select(
            SalesAnalytics.item_id,
            func.sum(SalesAnalytics.quantity_sold).label("total_sold"),
            func.sum(SalesAnalytics.total_revenue).label("total_revenue"),
            func.avg(SalesAnalytics.unit_sale_price).label("avg_price"),
        ).where(
            SalesAnalytics.warehouse_id == warehouse_id,
            SalesAnalytics.sale_date >= start_date,
            SalesAnalytics.sale_date <= end_date,
        ).group_by(SalesAnalytics.item_id)
        
        if item_group_id:
            stmt = stmt.join(Item).where(Item.item_group_id == item_group_id)
        
        sales_data = list(self.session.exec(stmt))
        
        # Get current stock levels
        stock_stmt = select(
            StockBalance.item_id,
            func.sum(StockBalance.quantity_on_hand).label("current_stock"),
        ).where(
            StockBalance.warehouse_id == warehouse_id,
        ).group_by(StockBalance.item_id)
        
        stock_data = {row.item_id: row.current_stock for row in self.session.exec(stock_stmt)}
        
        # Calculate turnover rates
        turnover_results = []
        for sale_row in sales_data:
            current_stock = stock_data.get(sale_row.item_id, Decimal('0'))
            avg_stock = (current_stock + sale_row.total_sold) / 2  # Simplified average
            
            turnover_rate = (sale_row.total_sold / avg_stock) if avg_stock > 0 else Decimal('0')
            days_of_supply = (current_stock / (sale_row.total_sold / period_days)) if sale_row.total_sold > 0 else float('inf')
            
            # Get item details
            item = self.session.get(Item, sale_row.item_id)
            
            turnover_results.append({
                "item_id": str(sale_row.item_id),
                "item_name": item.item_name if item else "Unknown",
                "sku": item.stock_keeping_unit if item else "Unknown",
                "total_sold": float(sale_row.total_sold),
                "total_revenue": float(sale_row.total_revenue),
                "current_stock": float(current_stock),
                "turnover_rate": float(turnover_rate),
                "days_of_supply": float(days_of_supply) if days_of_supply != float('inf') else None,
                "avg_price": float(sale_row.avg_price),
            })
        
        # Sort by turnover rate descending
        return sorted(turnover_results, key=lambda x: x["turnover_rate"], reverse=True)
    
    def get_abc_analysis(
        self,
        warehouse_id: UUID,
        user_id: UUID,
        period_days: int = 365,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Perform ABC analysis on inventory items."""
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=period_days)
        
        # Get sales data
        stmt = select(
            SalesAnalytics.item_id,
            func.sum(SalesAnalytics.total_revenue).label("total_revenue"),
            func.sum(SalesAnalytics.quantity_sold).label("total_quantity"),
        ).where(
            SalesAnalytics.warehouse_id == warehouse_id,
            SalesAnalytics.sale_date >= start_date,
            SalesAnalytics.sale_date <= end_date,
        ).group_by(SalesAnalytics.item_id)
        
        sales_data = list(self.session.exec(stmt))
        
        # Calculate total revenue
        total_revenue = sum(row.total_revenue for row in sales_data)
        
        # Sort by revenue descending and calculate cumulative percentages
        sorted_items = sorted(sales_data, key=lambda x: x.total_revenue, reverse=True)
        
        cumulative_revenue = Decimal('0')
        abc_results = {"A": [], "B": [], "C": []}
        
        for row in sorted_items:
            cumulative_revenue += row.total_revenue
            cumulative_percentage = (cumulative_revenue / total_revenue * 100) if total_revenue > 0 else 0
            
            # Get item details
            item = self.session.get(Item, row.item_id)
            
            item_data = {
                "item_id": str(row.item_id),
                "item_name": item.item_name if item else "Unknown",
                "sku": item.stock_keeping_unit if item else "Unknown",
                "total_revenue": float(row.total_revenue),
                "total_quantity": float(row.total_quantity),
                "revenue_percentage": float(row.total_revenue / total_revenue * 100) if total_revenue > 0 else 0,
                "cumulative_percentage": float(cumulative_percentage),
            }
            
            # Classify into ABC categories
            if cumulative_percentage <= 80:
                abc_results["A"].append(item_data)
            elif cumulative_percentage <= 95:
                abc_results["B"].append(item_data)
            else:
                abc_results["C"].append(item_data)
        
        return abc_results
    
    def get_slow_moving_items(
        self,
        warehouse_id: UUID,
        user_id: UUID,
        days_threshold: int = 90,
        min_stock_level: Decimal = Decimal('1'),
    ) -> List[Dict[str, Any]]:
        """Identify slow-moving inventory items."""
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_threshold)
        
        # Get items with stock but no recent sales
        stock_stmt = select(
            StockBalance.item_id,
            func.sum(StockBalance.quantity_on_hand).label("total_stock"),
        ).where(
            StockBalance.warehouse_id == warehouse_id,
            StockBalance.quantity_on_hand >= min_stock_level,
        ).group_by(StockBalance.item_id)
        
        items_with_stock = {row.item_id: row.total_stock for row in self.session.exec(stock_stmt)}
        
        # Get items with recent sales
        recent_sales_stmt = select(SalesAnalytics.item_id.distinct()).where(
            SalesAnalytics.warehouse_id == warehouse_id,
            SalesAnalytics.sale_date >= cutoff_date,
        )
        
        items_with_recent_sales = {row for row in self.session.exec(recent_sales_stmt)}
        
        # Find slow-moving items
        slow_moving = []
        for item_id, stock_level in items_with_stock.items():
            if item_id not in items_with_recent_sales:
                # Get last sale date
                last_sale_stmt = select(
                    func.max(SalesAnalytics.sale_date).label("last_sale_date")
                ).where(SalesAnalytics.item_id == item_id)
                
                last_sale_result = self.session.exec(last_sale_stmt).first()
                last_sale_date = last_sale_result if last_sale_result else None
                
                # Get item details
                item = self.session.get(Item, item_id)
                
                slow_moving.append({
                    "item_id": str(item_id),
                    "item_name": item.item_name if item else "Unknown",
                    "sku": item.stock_keeping_unit if item else "Unknown",
                    "current_stock": float(stock_level),
                    "last_sale_date": last_sale_date.isoformat() if last_sale_date else None,
                    "days_since_last_sale": (datetime.utcnow() - last_sale_date).days if last_sale_date else None,
                })
        
        # Sort by stock level descending (highest stock first)
        return sorted(slow_moving, key=lambda x: x["current_stock"], reverse=True)
    
    def generate_purchase_recommendations(
        self,
        warehouse_id: UUID,
        user_id: UUID,
        forecast_days: int = 30,
        safety_stock_days: int = 7,
    ) -> List[PurchaseRecommendation]:
        """Generate purchase recommendations based on sales velocity."""
        
        # Calculate sales velocity for each item
        end_date = datetime.utcnow()
        analysis_period = 90  # days
        start_date = end_date - timedelta(days=analysis_period)
        
        # Get sales data
        stmt = select(
            SalesAnalytics.item_id,
            func.sum(SalesAnalytics.quantity_sold).label("total_sold"),
            func.count(SalesAnalytics.sales_analytics_id).label("sale_count"),
        ).where(
            SalesAnalytics.warehouse_id == warehouse_id,
            SalesAnalytics.sale_date >= start_date,
            SalesAnalytics.sale_date <= end_date,
        ).group_by(SalesAnalytics.item_id)
        
        sales_data = {row.item_id: {
            "total_sold": row.total_sold,
            "sale_count": row.sale_count,
            "avg_daily_sales": row.total_sold / analysis_period,
        } for row in self.session.exec(stmt)}
        
        # Get current stock levels
        stock_stmt = select(
            StockBalance.item_id,
            func.sum(StockBalance.quantity_on_hand).label("current_stock"),
            func.sum(StockBalance.quantity_reserved).label("reserved_stock"),
        ).where(
            StockBalance.warehouse_id == warehouse_id,
        ).group_by(StockBalance.item_id)
        
        stock_data = {row.item_id: {
            "current_stock": row.current_stock,
            "reserved_stock": row.reserved_stock,
            "available_stock": row.current_stock - row.reserved_stock,
        } for row in self.session.exec(stock_stmt)}
        
        # Generate recommendations
        recommendations = []
        
        for item_id, stock_info in stock_data.items():
            sales_info = sales_data.get(item_id, {
                "total_sold": Decimal('0'),
                "sale_count": 0,
                "avg_daily_sales": Decimal('0'),
            })
            
            avg_daily_sales = sales_info["avg_daily_sales"]
            available_stock = stock_info["available_stock"]
            
            # Calculate days of stock remaining
            days_remaining = (available_stock / avg_daily_sales) if avg_daily_sales > 0 else float('inf')
            
            # Determine if reorder is needed
            reorder_needed = days_remaining <= (forecast_days + safety_stock_days)
            
            if reorder_needed and avg_daily_sales > 0:
                # Calculate recommended order quantity
                forecast_demand = avg_daily_sales * forecast_days
                safety_stock = avg_daily_sales * safety_stock_days
                recommended_quantity = forecast_demand + safety_stock - available_stock
                
                # Calculate priority score (0-100)
                urgency_factor = max(0, (forecast_days + safety_stock_days - days_remaining) / forecast_days)
                velocity_factor = min(1, avg_daily_sales / 10)  # Normalize to reasonable range
                priority_score = (urgency_factor * 70 + velocity_factor * 30)
                
                # Determine sales trend
                recent_sales = self._get_recent_sales_trend(item_id, warehouse_id, 30)
                trend = self._calculate_trend(recent_sales)
                
                # Get item details
                item = self.session.get(Item, item_id)
                
                recommendation = PurchaseRecommendation(
                    item_id=item_id,
                    warehouse_id=warehouse_id,
                    current_stock=stock_info["current_stock"],
                    reserved_stock=stock_info["reserved_stock"],
                    available_stock=available_stock,
                    avg_daily_sales=avg_daily_sales,
                    sales_velocity_trend=trend,
                    days_of_stock_remaining=int(days_remaining) if days_remaining != float('inf') else None,
                    recommended_order_quantity=max(Decimal('1'), recommended_quantity),
                    recommended_order_date=date.today(),
                    priority_score=Decimal(str(round(priority_score, 2))),
                    recommendation_reason=f"Stock will run out in {int(days_remaining)} days",
                    seasonal_factor=self._calculate_seasonal_factor(item_id, warehouse_id),
                    is_active=True,
                )
                
                recommendations.append(recommendation)
        
        # Sort by priority score descending
        recommendations.sort(key=lambda x: x.priority_score, reverse=True)
        
        # Save recommendations to database
        for rec in recommendations:
            # Check if recommendation already exists
            existing_stmt = select(PurchaseRecommendation).where(
                PurchaseRecommendation.item_id == rec.item_id,
                PurchaseRecommendation.warehouse_id == rec.warehouse_id,
                PurchaseRecommendation.is_active == True,
            )
            existing = self.session.exec(existing_stmt).first()
            
            if existing:
                # Update existing recommendation
                existing.current_stock = rec.current_stock
                existing.reserved_stock = rec.reserved_stock
                existing.available_stock = rec.available_stock
                existing.avg_daily_sales = rec.avg_daily_sales
                existing.sales_velocity_trend = rec.sales_velocity_trend
                existing.days_of_stock_remaining = rec.days_of_stock_remaining
                existing.recommended_order_quantity = rec.recommended_order_quantity
                existing.priority_score = rec.priority_score
                existing.recommendation_reason = rec.recommendation_reason
                existing.calculated_at = datetime.utcnow()
            else:
                self.session.add(rec)
        
        self.session.commit()
        return recommendations
    
    def get_marketplace_performance(
        self,
        warehouse_id: UUID,
        user_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Get performance metrics by marketplace channel."""
        
        stmt = select(
            SalesAnalytics.marketplace_channel,
            func.sum(SalesAnalytics.quantity_sold).label("total_quantity"),
            func.sum(SalesAnalytics.total_revenue).label("total_revenue"),
            func.sum(SalesAnalytics.total_cost).label("total_cost"),
            func.sum(SalesAnalytics.gross_margin).label("total_margin"),
            func.avg(SalesAnalytics.margin_percentage).label("avg_margin_pct"),
            func.count(SalesAnalytics.sales_analytics_id).label("order_count"),
            func.count(SalesAnalytics.item_id.distinct()).label("unique_items"),
        ).where(SalesAnalytics.warehouse_id == warehouse_id)
        
        if start_date:
            stmt = stmt.where(SalesAnalytics.sale_date >= start_date)
        if end_date:
            stmt = stmt.where(SalesAnalytics.sale_date <= end_date)
        
        stmt = stmt.group_by(SalesAnalytics.marketplace_channel)
        
        results = []
        for row in self.session.exec(stmt):
            results.append({
                "marketplace_channel": row.marketplace_channel,
                "total_quantity": float(row.total_quantity or 0),
                "total_revenue": float(row.total_revenue or 0),
                "total_cost": float(row.total_cost or 0),
                "total_margin": float(row.total_margin or 0),
                "avg_margin_percentage": float(row.avg_margin_pct or 0),
                "order_count": row.order_count,
                "unique_items": row.unique_items,
                "avg_order_value": float((row.total_revenue or 0) / row.order_count) if row.order_count > 0 else 0,
            })
        
        return sorted(results, key=lambda x: x["total_revenue"], reverse=True)
    
    def _group_analytics_results(self, analytics: List[SalesAnalytics], group_by: str) -> List[Dict[str, Any]]:
        """Group analytics results by specified dimension."""
        
        grouped = {}
        
        for record in analytics:
            if group_by == "day":
                key = record.sale_date.date().isoformat()
            elif group_by == "week":
                week_start = record.sale_date.date() - timedelta(days=record.sale_date.weekday())
                key = week_start.isoformat()
            elif group_by == "month":
                key = record.sale_date.strftime("%Y-%m")
            elif group_by == "item":
                key = str(record.item_id)
            elif group_by == "marketplace":
                key = record.marketplace_channel
            else:
                key = "total"
            
            if key not in grouped:
                grouped[key] = {
                    "group_key": key,
                    "total_quantity": Decimal('0'),
                    "total_revenue": Decimal('0'),
                    "total_cost": Decimal('0'),
                    "total_margin": Decimal('0'),
                    "order_count": 0,
                }
            
            grouped[key]["total_quantity"] += record.quantity_sold
            grouped[key]["total_revenue"] += record.total_revenue
            grouped[key]["total_cost"] += record.total_cost or Decimal('0')
            grouped[key]["total_margin"] += record.gross_margin or Decimal('0')
            grouped[key]["order_count"] += 1
        
        # Convert to list and add calculated fields
        results = []
        for group_data in grouped.values():
            group_data["avg_margin_percentage"] = (
                (group_data["total_margin"] / group_data["total_revenue"] * 100)
                if group_data["total_revenue"] > 0 else Decimal('0')
            )
            group_data["avg_order_value"] = (
                group_data["total_revenue"] / group_data["order_count"]
                if group_data["order_count"] > 0 else Decimal('0')
            )
            
            # Convert Decimals to floats for JSON serialization
            for key, value in group_data.items():
                if isinstance(value, Decimal):
                    group_data[key] = float(value)
            
            results.append(group_data)
        
        return sorted(results, key=lambda x: x["group_key"])
    
    def _get_recent_sales_trend(self, item_id: UUID, warehouse_id: UUID, days: int) -> List[Decimal]:
        """Get recent sales data for trend calculation."""
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        stmt = select(
            func.date(SalesAnalytics.sale_date).label("sale_date"),
            func.sum(SalesAnalytics.quantity_sold).label("daily_sales"),
        ).where(
            SalesAnalytics.item_id == item_id,
            SalesAnalytics.warehouse_id == warehouse_id,
            SalesAnalytics.sale_date >= start_date,
        ).group_by(func.date(SalesAnalytics.sale_date)).order_by("sale_date")
        
        return [row.daily_sales for row in self.session.exec(stmt)]
    
    def _calculate_trend(self, sales_data: List[Decimal]) -> str:
        """Calculate sales trend from recent data."""
        
        if len(sales_data) < 3:
            return "stable"
        
        # Simple trend calculation - compare first half to second half
        mid_point = len(sales_data) // 2
        first_half_avg = sum(sales_data[:mid_point]) / mid_point
        second_half_avg = sum(sales_data[mid_point:]) / (len(sales_data) - mid_point)
        
        if second_half_avg > first_half_avg * Decimal('1.1'):
            return "increasing"
        elif second_half_avg < first_half_avg * Decimal('0.9'):
            return "decreasing"
        else:
            return "stable"
    
    def _calculate_seasonal_factor(self, item_id: UUID, warehouse_id: UUID) -> Decimal:
        """Calculate seasonal factor for item (simplified)."""
        
        # This is a placeholder - would implement proper seasonal analysis
        current_month = datetime.utcnow().month
        
        # Simple seasonal factors (would be more sophisticated in practice)
        seasonal_factors = {
            12: Decimal('1.3'),  # December - holiday season
            11: Decimal('1.2'),  # November
            1: Decimal('0.8'),   # January - post-holiday
            2: Decimal('0.8'),   # February
        }
        
        return seasonal_factors.get(current_month, Decimal('1.0'))