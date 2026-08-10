"""初始化数据库默认数据"""
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app import models


def init_db():
    # 创建所有表
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # 检查是否已有数据
        if db.query(models.DeviceStatus).first():
            print("数据库已有数据，跳过初始化")
            return

        # 初始化默认状态
        default_statuses = [
            models.DeviceStatus(name="在用", color="#67C23A", sort_order=1),
            models.DeviceStatus(name="维修", color="#E6A23C", sort_order=2),
            models.DeviceStatus(name="淘汰", color="#909399", sort_order=3),
            models.DeviceStatus(name="闲置", color="#409EFF", sort_order=4),
        ]
        for s in default_statuses:
            db.add(s)

        # 初始化根文件夹
        root_folder = models.Folder(name="黄山健康职业学院", parent_id=None, sort_order=0)
        db.add(root_folder)
        db.flush()  # 获取ID

        # 初始化示例部门文件夹
        depts = ["信息中心", "教务处", "学生处", "财务处", "后勤处"]
        for i, dept in enumerate(depts):
            dept_folder = models.Folder(name=dept, parent_id=root_folder.id, sort_order=i)
            db.add(dept_folder)
            db.flush()

            # 每个部门下创建设备类型子文件夹
            types = ["电脑", "打印机", "交换机", "其他设备"]
            for j, t in enumerate(types):
                type_folder = models.Folder(name=t, parent_id=dept_folder.id, sort_order=j)
                db.add(type_folder)

        # 初始化示例自定义字段
        default_fields = [
            models.CustomField(name="购买日期", field_type="date", is_required=False, sort_order=1),
            models.CustomField(name="保修期(月)", field_type="number", is_required=False, sort_order=2),
            models.CustomField(name="资产编号", field_type="text", is_required=True, sort_order=3),
            models.CustomField(name="品牌", field_type="text", is_required=False, sort_order=4),
        ]
        for f in default_fields:
            db.add(f)

        # 初始化示例设备
        sample_device = models.Device(
            name="信息中心-办公电脑-01",
            device_type="电脑",
            mac_address="00:1A:2B:3C:4D:5E",
            ip_address="192.168.1.101",
            department="信息中心",
            user="张三",
            status_id=1,
            folder_id=3,  # 信息中心/电脑
            description="联想ThinkCentre，2024年采购"
        )
        db.add(sample_device)

        db.commit()
        print("数据库初始化完成！")
        print("默认创建了：")
        print("- 4个设备状态")
        print("- 5个部门文件夹（含子文件夹）")
        print("- 4个自定义字段")
        print("- 1个示例设备")

    finally:
        db.close()


if __name__ == "__main__":
    init_db()
